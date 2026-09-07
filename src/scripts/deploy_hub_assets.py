#!/usr/bin/env python3
"""Deploy the LSEG Intelligence Hub Dataverse table and web resources."""

from __future__ import annotations

import os

import base64
import json
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import dv  # noqa: E402


EXPECTED_ORG = os.environ.get("DATAVERSE_URL", "").rstrip("/")
SOLUTION = "lseg_BankableWalletIntelligence"
ENTITY_LOGICAL = "lseg_intelligenceanalysis"
ENTITY_SCHEMA = "lseg_IntelligenceAnalysis"
H = {"MSCRM.SolutionUniqueName": SOLUTION}
HUB_WEBRESOURCE = "lseg_/intelligence-hub-v7.html"
STATIC_RESOURCES = [
    ("lseg_/lseg-icon.png", "LSEG Agent Icon", 5, "lseg-icon.png"),
    (
        "lseg_/copilot-studio.png",
        "Microsoft Copilot Studio Icon",
        5,
        "copilot-studio.png",
    ),
]


def api_long(method: str, path: str, body: dict) -> dict:
    headers = {
        "Authorization": f"Bearer {dv._token()}",
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
        **H,
    }
    request = Request(
        dv._url(path),
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method=method,
    )
    with urlopen(request, timeout=300) as response:
        content = response.read()
        return json.loads(content) if content else {"headers": dict(response.headers)}


def label(text: str) -> dict:
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.Label",
        "LocalizedLabels": [
            {
                "@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
                "Label": text,
                "LanguageCode": 1033,
            }
        ],
    }


def required() -> dict:
    return {
        "Value": "None",
        "CanBeChanged": True,
        "ManagedPropertyLogicalName": "canmodifyrequirementlevelsettings",
    }


def string_attr(schema: str, display: str, max_length: int = 300) -> dict:
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
        "SchemaName": schema,
        "MaxLength": max_length,
        "FormatName": {"Value": "Text"},
        "RequiredLevel": required(),
        "DisplayName": label(display),
        "Description": label(""),
    }


def memo_attr(schema: str, display: str, max_length: int = 1048576) -> dict:
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.MemoAttributeMetadata",
        "SchemaName": schema,
        "MaxLength": max_length,
        "Format": "TextArea",
        "RequiredLevel": required(),
        "DisplayName": label(display),
        "Description": label(""),
    }


def status_attr(schema: str, display: str) -> dict:
    options = ["Queued", "Running", "Completed", "Failed"]
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.PicklistAttributeMetadata",
        "SchemaName": schema,
        "RequiredLevel": required(),
        "DisplayName": label(display),
        "Description": label(""),
        "OptionSet": {
            "@odata.type": "Microsoft.Dynamics.CRM.OptionSetMetadata",
            "OptionSetType": "Picklist",
            "IsGlobal": False,
            "Options": [
                {"Value": 100000000 + index, "Label": label(value)}
                for index, value in enumerate(options)
            ],
        },
    }


AGENT_COLUMNS = [
    ("Orchestrator", "RM Orchestrator"),
    ("Wallet", "Bankable Wallet"),
    ("Pricing", "Dynamic Pricing"),
    ("Risk", "Credit and Risk"),
    ("AccountPlan", "Account Planning"),
    ("Trade", "Trade Intelligence"),
]


def table_exists() -> bool:
    try:
        dv.api(
            "GET",
            f"/EntityDefinitions(LogicalName='{ENTITY_LOGICAL}')?$select=LogicalName",
        )
        return True
    except Exception:
        return False


def create_table() -> None:
    attributes = [
        {
            "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
            "SchemaName": "lseg_Name",
            "MaxLength": 300,
            "FormatName": {"Value": "Text"},
            "RequiredLevel": required(),
            "IsPrimaryName": True,
            "DisplayName": label("Name"),
            "Description": label("Analysis run name"),
        },
    ]
    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
        "SchemaName": ENTITY_SCHEMA,
        "LogicalName": ENTITY_LOGICAL,
        "DisplayName": label("LSEG Intelligence Analysis"),
        "DisplayCollectionName": label("LSEG Intelligence Analyses"),
        "Description": label("Tracks six-agent LSEG company intelligence runs."),
        "HasActivities": False,
        "HasNotes": True,
        "IsActivity": False,
        "OwnershipType": "UserOwned",
        "PrimaryNameAttribute": "lseg_name",
        "Attributes": attributes,
    }
    api_long("POST", "/EntityDefinitions", body)
    print("Created LSEG Intelligence Analysis table")
    ensure_missing_columns()


def ensure_missing_columns() -> None:
    existing = dv.api(
        "GET",
        f"/EntityDefinitions(LogicalName='{ENTITY_LOGICAL}')/Attributes?$select=LogicalName",
    ).get("value", [])
    names = {row["LogicalName"] for row in existing}
    columns = [
        ("lseg_companyname", string_attr("lseg_CompanyName", "Company Name", 300)),
        ("lseg_lei", string_attr("lseg_LEI", "Legal Entity Identifier", 20)),
        ("lseg_country", string_attr("lseg_Country", "Country", 10)),
        ("lseg_status", status_attr("lseg_Status", "Overall Status")),
        ("lseg_resultjson", memo_attr("lseg_ResultJson", "Consolidated Result JSON")),
        ("lseg_error", memo_attr("lseg_Error", "Error Details", 100000)),
    ]
    for suffix, display in AGENT_COLUMNS:
        columns.extend(
            [
                (
                    f"lseg_{suffix.lower()}status",
                    status_attr(f"lseg_{suffix}Status", f"{display} Status"),
                ),
                (
                    f"lseg_{suffix.lower()}result",
                    memo_attr(f"lseg_{suffix}Result", f"{display} Result"),
                ),
            ]
        )
    for logical_name, metadata in columns:
        if logical_name in names:
            continue
        dv.api(
            "POST",
            f"/EntityDefinitions(LogicalName='{ENTITY_LOGICAL}')/Attributes",
            metadata,
            headers=H,
        )
        print(f"Created column {logical_name}")


def publish_webresource(name: str, display: str, kind: int, path: Path) -> str:
    content = base64.b64encode(path.read_bytes()).decode("ascii")
    rows = dv.api(
        "GET",
        f"/webresourceset?$select=webresourceid&$filter=name eq '{name}'",
    ).get("value", [])
    body = {
        "name": name,
        "displayname": display,
        "webresourcetype": kind,
        "content": content,
    }
    if rows:
        webresource_id = rows[0]["webresourceid"]
        dv.api("PATCH", f"/webresourceset({webresource_id})", body, headers=H)
        print(f"Updated {name}")
    else:
        row = dv.api(
            "POST",
            "/webresourceset",
            body,
            headers={**H, "Prefer": "return=representation"},
        )
        webresource_id = row["webresourceid"]
        print(f"Created {name}")
    try:
        api_long(
            "POST",
            "/PublishXml",
            {
                "ParameterXml": (
                    "<importexportxml><webresources><webresource>"
                    f"{webresource_id}"
                    "</webresource></webresources></importexportxml>"
                )
            },
        )
    except HTTPError as exc:
        if exc.code != 400:
            raise
        print(f"Deferred publishing {name} to PublishAllXml")
    return webresource_id


def webresource_exists(name: str) -> bool:
    return bool(
        dv.api(
            "GET",
            f"/webresourceset?$select=webresourceid&$filter=name eq '{name}'",
        ).get("value", [])
    )


def verify() -> None:
    metadata = dv.api(
        "GET",
        f"/EntityDefinitions(LogicalName='{ENTITY_LOGICAL}')?$select=LogicalName,EntitySetName",
    )
    attrs = dv.api(
        "GET",
        f"/EntityDefinitions(LogicalName='{ENTITY_LOGICAL}')/Attributes?$select=LogicalName",
    ).get("value", [])
    names = {row["LogicalName"] for row in attrs}
    expected = {
        "lseg_companyname",
        "lseg_lei",
        "lseg_status",
        "lseg_resultjson",
        *(f"lseg_{suffix.lower()}status" for suffix, _ in AGENT_COLUMNS),
        *(f"lseg_{suffix.lower()}result" for suffix, _ in AGENT_COLUMNS),
    }
    missing = expected - names
    if missing:
        raise RuntimeError(f"Missing analysis columns: {sorted(missing)}")
    resources = dv.api(
        "GET",
        "/webresourceset?$select=name,webresourceid"
        f"&$filter=name eq '{HUB_WEBRESOURCE}'"
        + "".join(f" or name eq '{name}'" for name, *_ in STATIC_RESOURCES),
    ).get("value", [])
    if len(resources) != 1 + len(STATIC_RESOURCES):
        raise RuntimeError("Hub web resources were not found after publishing")
    print(
        f"Verified {metadata['LogicalName']} ({metadata['EntitySetName']}), "
        f"{len(expected)} required columns, and {len(resources)} web resources"
    )


def main() -> None:
    if dv.org_url().rstrip("/").lower() != EXPECTED_ORG:
        raise RuntimeError(f"Active environment is not PTA OCS: {dv.org_url()}")
    if not table_exists():
        create_table()
    else:
        ensure_missing_columns()
    for name, display, kind, filename in STATIC_RESOURCES:
        if webresource_exists(name):
            print(f"Keeping existing {name}")
            continue
        publish_webresource(name, display, kind, ASSET_ROOT / filename)
    hub_id = publish_webresource(
        HUB_WEBRESOURCE,
        "LSEG Intelligence Hub v7",
        1,
        ASSET_ROOT / "lseg-intelligence-hub.html",
    )
    try:
        api_long("POST", "/PublishAllXml", {})
    except HTTPError as exc:
        if exc.code != 400:
            raise
        print("PublishAllXml deferred to app-specific publication")
    verify()
    print(f"HUB_WEBRESOURCE_ID={hub_id}")
    print(f"HUB_URL={EXPECTED_ORG}/WebResources/{HUB_WEBRESOURCE}")


if __name__ == "__main__":
    main()
