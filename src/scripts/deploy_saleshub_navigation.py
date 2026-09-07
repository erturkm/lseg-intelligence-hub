#!/usr/bin/env python3
"""Add LSEG Intelligence Hub v7 to Sales Hub immediately after GLEIF."""

from __future__ import annotations

import os

import sys
import uuid
import xml.etree.ElementTree as ET
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import dv  # noqa: E402


EXPECTED_ORG = os.environ.get("DATAVERSE_URL", "").rstrip("/")
SOLUTION = "lseg_BankableWalletIntelligence"
APP_ID = "c2df169c-f557-eb11-bb23-000d3a26d466"
APP_UNIQUE_ID = "bd6a2ac2-4543-4edf-940e-14c7e47c8249"
SITEMAP_ID = "c0df169c-f557-eb11-bb23-000d3a26d466"
WEBRESOURCE_NAME = "lseg_/intelligence-hub-v7.html"
GLEIF_SUBAREA_ID = "subarea_gleif_corporate_hierarchy"
LSEG_SUBAREA_ID = "subarea_lseg_intelligence_hub_v7"
LEGACY_SUBAREA_IDS = {"lseg_intelligence_hub", "subarea_lseg_intelligence_hub_v6"}
HEADERS = {"MSCRM.SolutionUniqueName": SOLUTION}


def api_long(method: str, path: str, body: dict) -> dict:
    headers = {
        "Authorization": f"Bearer {dv._token()}",
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
        **HEADERS,
    }
    request = Request(
        dv._url(path),
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method=method,
    )
    with urlopen(request, timeout=300) as response:
        content = response.read()
        return json.loads(content) if content else {}


def lookup_webresource() -> str:
    rows = dv.api(
        "GET",
        f"/webresourceset?$select=webresourceid&$filter=name eq '{WEBRESOURCE_NAME}'",
    ).get("value", [])
    if not rows:
        raise RuntimeError(f"Missing web resource: {WEBRESOURCE_NAME}")
    return rows[0]["webresourceid"]


def ensure_sitemap_entry() -> None:
    row = dv.api("GET", f"/sitemaps({SITEMAP_ID})?$select=sitemapxml")
    root = ET.fromstring(row["sitemapxml"])

    target_group = None
    gleif_index = None
    existing = None
    for group in root.findall(".//Group"):
        children = list(group)
        for index, child in enumerate(children):
            if child.tag != "SubArea":
                continue
            subarea_id = child.attrib.get("Id")
            if subarea_id == GLEIF_SUBAREA_ID:
                target_group = group
                gleif_index = index
            elif subarea_id == LSEG_SUBAREA_ID:
                existing = (group, child)
            elif subarea_id in LEGACY_SUBAREA_IDS:
                group.remove(child)

    if target_group is None or gleif_index is None:
        raise RuntimeError(f"Could not find GLEIF subarea {GLEIF_SUBAREA_ID}.")

    if existing:
        existing[0].remove(existing[1])
    gleif_index = list(target_group).index(
        next(
            child
            for child in target_group
            if child.tag == "SubArea"
            and child.attrib.get("Id") == GLEIF_SUBAREA_ID
        )
    )

    subarea = ET.Element(
        "SubArea",
        {
            "Id": LSEG_SUBAREA_ID,
            "Url": f"$webresource:{WEBRESOURCE_NAME}",
            "AvailableOffline": "false",
            "PassParams": "true",
            "Title": "LSEG Intelligence Hub",
        },
    )
    titles = ET.SubElement(subarea, "Titles")
    ET.SubElement(titles, "Title", {"LCID": "1033", "Title": "LSEG Intelligence Hub"})
    target_group.insert(gleif_index + 1, subarea)

    xml = '<?xml version="1.0" encoding="utf-8"?>' + ET.tostring(
        root, encoding="unicode", short_empty_elements=True
    )
    api_long("PATCH", f"/sitemaps({SITEMAP_ID})", {"sitemapxml": xml})


def ensure_app_component(webresource_id: str) -> None:
    existing = dv.api(
        "GET",
        f"/appmodulecomponents?$select=appmodulecomponentid"
        f"&$filter=_appmoduleidunique_value eq {APP_UNIQUE_ID} and objectid eq {webresource_id}",
    ).get("value", [])
    if existing:
        return
    try:
        dv.api(
            "POST",
            f"/appmodules({APP_ID})/Microsoft.Dynamics.CRM.AddAppComponents",
            {
                "Components": [
                    {
                        "@odata.type": "#Microsoft.Dynamics.CRM.expando",
                        "ObjectId": webresource_id,
                        "ComponentType": 61,
                    }
                ]
            },
        )
    except Exception as exc:
        message = str(exc)
        if "Resource not found for the segment 'Microsoft.Dynamics.CRM.AddAppComponents'" in message:
            try:
                dv.api(
                    "POST",
                    "/appmodulecomponents",
                    {
                        "objectid": webresource_id,
                        "componenttype": 61,
                        "appmodulecomponentidunique": str(uuid.uuid4()),
                        "appmoduleid@odata.bind": f"/appmodules({APP_ID})",
                    },
                    headers=HEADERS,
                )
            except Exception as direct_exc:
                if "does not support entities of type 'appmodulecomponent'" not in str(direct_exc):
                    raise
                print("App component API unavailable; sitemap web-resource reference retained")
            return
        if "already exists" not in message and "same key" not in message:
            raise


def publish(webresource_id: str) -> None:
    parameter_xml = (
        "<importexportxml>"
        f"<webresources><webresource>{webresource_id}</webresource></webresources>"
        f"<sitemaps><sitemap>{SITEMAP_ID}</sitemap></sitemaps>"
        f"<appmodules><appmodule>{APP_ID}</appmodule></appmodules>"
        "</importexportxml>"
    )
    try:
        dv.api("POST", "/PublishXml", {"ParameterXml": parameter_xml})
    except Exception as exc:
        print(f"PublishXml warning: {exc}")
    try:
        dv.api("POST", "/PublishAppForUser", {"AppModuleId": APP_ID})
    except Exception as exc:
        if "Resource not found for the segment 'PublishAppForUser'" not in str(exc):
            raise
        print("PublishAppForUser unavailable; saved sitemap remains authoritative")


def verify(webresource_id: str) -> None:
    sitemap = dv.api("GET", f"/sitemaps({SITEMAP_ID})?$select=sitemapxml")
    root = ET.fromstring(sitemap["sitemapxml"])
    for group in root.findall(".//Group"):
        subareas = [
            child.attrib.get("Id")
            for child in group
            if child.tag == "SubArea"
        ]
        if GLEIF_SUBAREA_ID in subareas:
            expected_index = subareas.index(GLEIF_SUBAREA_ID) + 1
            if expected_index >= len(subareas) or subareas[expected_index] != LSEG_SUBAREA_ID:
                raise RuntimeError("LSEG subarea is not immediately after GLEIF.")
            lseg = next(
                child
                for child in group
                if child.tag == "SubArea"
                and child.attrib.get("Id") == LSEG_SUBAREA_ID
            )
            if lseg.attrib.get("Url") != f"$webresource:{WEBRESOURCE_NAME}":
                raise RuntimeError("LSEG subarea does not reference the v7 web resource.")
            break
    else:
        raise RuntimeError("GLEIF and LSEG navigation entries were not found.")

    components = dv.api(
        "GET",
        f"/appmodulecomponents?$select=objectid,componenttype"
        f"&$filter=_appmoduleidunique_value eq {APP_UNIQUE_ID} and objectid eq {webresource_id}",
    ).get("value", [])
    if not components:
        print("Verified v7 through the Sales Hub sitemap web-resource reference")


def main() -> None:
    if dv.org_url().rstrip("/") != EXPECTED_ORG:
        raise RuntimeError(f"Refusing deployment to unexpected org: {dv.org_url()}")
    webresource_id = lookup_webresource()
    ensure_sitemap_entry()
    ensure_app_component(webresource_id)
    publish(webresource_id)
    verify(webresource_id)
    print("LSEG Intelligence Hub v7 added immediately after GLEIF in Sales Hub.")
    print(f"Sales Hub: {EXPECTED_ORG}/main.aspx?appid={APP_ID}")


if __name__ == "__main__":
    main()
