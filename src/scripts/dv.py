#!/usr/bin/env python3
"""Small Dataverse Web API helper backed by the active PAC auth profile."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import msal

API_VERSION = "v9.2"
PAC_CLIENT_ID = "be8a5c48-2260-4275-ac53-978f618dcaf4"
PAC_APP_SUPPORT = Path.home() / "Library" / "Application Support" / "Microsoft" / "PowerAppsCli"
PAC_PROFILES = PAC_APP_SUPPORT / "authprofiles_v2.json"
PAC_KEYCHAIN_ITEMS = [
    ("powerplatform_cli_service", "powerplatform_cli_account"),
    ("msal-extensions", "b330354a383e2c01d96b243e40dc223adc3a24ca67983bb901bb354b0f53c719"),
    ("Microsoft.Developer.IdentityService", "MSALCache"),
]


class DataverseError(RuntimeError):
    pass


def _pac_env() -> dict[str, str]:
    env = os.environ.copy()
    env["DOTNET_ROOT"] = str(Path.home() / ".dotnet")
    env["PATH"] = f"{Path.home() / '.dotnet'}:{Path.home() / '.dotnet' / 'tools'}:{env.get('PATH', '')}"
    return env


def _active_profile() -> dict[str, Any]:
    if PAC_PROFILES.exists():
        data = json.loads(PAC_PROFILES.read_text())
        current = data.get("Current", {}).get("UNIVERSAL")
        if current and current.get("Resource"):
            return current

    result = subprocess.run(
        ["pac", "auth", "list"],
        env=_pac_env(),
        check=True,
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        if "*" in line and "https://" in line:
            org_url = re.search(r"https://\S+", line)
            if org_url:
                return {"Resource": org_url.group(0)}
    raise DataverseError("No active PAC auth profile found. Run: pac auth create --url <org-url>")


def org_url() -> str:
    return _active_profile()["Resource"].rstrip("/")


def _decode_keychain_password(value: str) -> str:
    value = value.strip()
    try:
        return bytes.fromhex(value).decode("utf-8")
    except ValueError:
        return value


def _msal_cache_payloads() -> list[str]:
    payloads: list[str] = []
    seen: set[str] = set()
    for service, account in PAC_KEYCHAIN_ITEMS:
        secret = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
            capture_output=True,
            text=True,
            check=False,
        )
        if secret.returncode == 0 and secret.stdout.strip():
            payload = _decode_keychain_password(secret.stdout)
            if payload not in seen:
                payloads.append(payload)
                seen.add(payload)

    result = subprocess.run(["security", "dump-keychain"], capture_output=True, text=True, check=False)
    accounts = re.findall(r'"acct"<blob>="([^"]+)".*?"svce"<blob>="msal-extensions"', result.stdout, re.S)
    for account in accounts:
        secret = subprocess.run(
            ["security", "find-generic-password", "-s", "msal-extensions", "-a", account, "-w"],
            capture_output=True,
            text=True,
            check=False,
        )
        if secret.returncode == 0 and secret.stdout.strip():
            payload = _decode_keychain_password(secret.stdout)
            if payload not in seen:
                payloads.append(payload)
                seen.add(payload)
    return payloads


def _cached_access_token(cache_payload: str) -> str | None:
    data = json.loads(cache_payload)
    org_targets = {
        f"{org_url()}/.default",
        f"{org_url()}//.default",
        f"{org_url()}/user_impersonation",
        f"{org_url()}//user_impersonation",
    }
    now = int(time.time())
    for token in data.get("AccessToken", {}).values():
        targets = set(str(token.get("target", "")).split())
        if targets & org_targets and int(token.get("expires_on", "0")) > now + 60:
            return token.get("secret")
    return None


def _token(force_refresh: bool = False) -> str:
    profile = _active_profile()
    authority = profile.get("Authority") or f"https://login.microsoftonline.com/{profile.get('TenantId', 'organizations')}/"
    scopes = [f"{org_url()}/.default"]

    for payload in _msal_cache_payloads():
        if not force_refresh:
            cached = _cached_access_token(payload)
            if cached:
                return cached
        # Skip the silent acquire (hangs when refresh token is expired) — fall through to az CLI

    # Fallback: Azure CLI
    try:
        command = ["az", "account", "get-access-token", "--resource", org_url().rstrip("/")]
        if tenant_id := profile.get("TenantId"):
            command.extend(["--tenant", tenant_id])
        result = subprocess.run(
            command,
            capture_output=True, text=True, timeout=20
        )
        if result.returncode == 0:
            tok = json.loads(result.stdout).get("accessToken")
            if tok:
                return tok
    except Exception:
        pass

    raise DataverseError("Could not acquire a Dataverse access token. Run: az login")


def _encode_odata_dollars(path: str) -> str:
    if "?" not in path:
        return path
    base, query = path.split("?", 1)
    return f"{base}?{query.replace('$', '%24')}"


def _url(path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    clean_path = path if path.startswith("/") else f"/{path}"
    encoded_path = _encode_odata_dollars(clean_path)
    split = urlsplit(encoded_path)
    quoted_path = quote(split.path, safe="/()=,'")
    quoted_query = quote(split.query, safe="%24=&(),',")
    return urlunsplit((org_url().split("://", 1)[0], org_url().split("://", 1)[1], f"/api/data/{API_VERSION}{quoted_path}", quoted_query, split.fragment))


def api(method: str, path: str, body: Any | None = None, headers: dict[str, str] | None = None, max_retries: int = 6) -> Any:
    request_headers = {
        "Authorization": f"Bearer {_token()}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }
    if body is not None:
        request_headers["Content-Type"] = "application/json; charset=utf-8"
    if headers:
        request_headers.update(headers)

    data = None if body is None else json.dumps(body).encode("utf-8")

    attempt = 0
    while True:
        attempt += 1
        request = Request(_url(path), data=data, headers=request_headers, method=method.upper())
        try:
            with urlopen(request, timeout=60) as response:
                content = response.read()
                if not content:
                    return {"headers": dict(response.headers)}
                return json.loads(content)
        except HTTPError as err:
            if err.code == 401 and attempt == 1:
                request_headers["Authorization"] = f"Bearer {_token(force_refresh=True)}"
                continue
            details = err.read().decode("utf-8", errors="replace")
            transient = err.code in (429, 503, 504) or (
                err.code in (500, 502) and (
                    "another [Import]" in details
                    or "solution is currently being imported" in details
                    or "Sql Number: 1205" in details
                    or "deadlock" in details.lower()
                    or "timed out" in details.lower()
                )
            )
            if transient and attempt < max_retries:
                wait = min(60, 5 * (2 ** (attempt - 1)))
                print(f"  [retry {attempt}/{max_retries}] HTTP {err.code}; waiting {wait}s")
                time.sleep(wait)
                continue
            raise DataverseError(f"{method.upper()} {path} failed with HTTP {err.code}: {details}") from err
        except URLError as err:
            if attempt < max_retries:
                wait = min(30, 3 * attempt)
                print(f"  [retry {attempt}/{max_retries}] network error {err}; waiting {wait}s")
                time.sleep(wait)
                continue
            raise DataverseError(f"{method.upper()} {path} network error: {err}") from err


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: dv.py METHOD PATH [JSON_BODY]", file=sys.stderr)
        raise SystemExit(2)
    payload = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
    print(json.dumps(api(sys.argv[1], sys.argv[2], payload), indent=2))
