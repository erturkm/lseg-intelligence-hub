#!/usr/bin/env python3
"""Create the LSEG Intelligence Hub model-driven app and navigation."""

from __future__ import annotations

import os

import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import dv  # noqa: E402


EXPECTED_ORG = os.environ.get("DATAVERSE_URL", "").rstrip("/")
SOLUTION = "lseg_BankableWalletIntelligence"
APP_NAME = "LSEG Intelligence Hub"
APP_UNIQUE = "lseg_IntelligenceHub"
SITEMAP_UNIQUE = "lseg_IntelligenceHub_sitemap"
WEBRESOURCE_NAME = "lseg_/intelligence-hub-v7.html"
ICON_NAME = "lseg_/lseg-icon.png"
HOST_APP_UNIQUE = "agn_RMCRM"
SUBAREA_ID = "lseg_intelligence_hub"
H = {"MSCRM.SolutionUniqueName": SOLUTION}

SITEMAP_XML = f"""<SiteMap>
  <Area Id="lseg_intelligence" ShowGroups="true" Title="LSEG Intelligence">
    <Group Id="lseg_hub_group" Title="Corporate Intelligence">
      <SubArea Id="lseg_hub" Url="$webresource:{WEBRESOURCE_NAME}"
        AvailableOffline="false" PassParams="true" Title="Intelligence Hub">
        <Titles>
          <Title LCID="1033" Title="LSEG Intelligence Hub" />
        </Titles>
      </SubArea>
    </Group>
  </Area>
</SiteMap>"""


def lookup_webresource(name: str) -> str:
    rows = dv.api(
        "GET",
        f"/webresourceset?$select=webresourceid&$filter=name eq '{name}'",
    ).get("value", [])
    if not rows:
        raise RuntimeError(f"Missing web resource: {name}")
    return rows[0]["webresourceid"]


def ensure_app() -> str:
    rows = dv.api(
        "GET",
        f"/appmodules?$select=appmoduleid&$filter=uniquename eq '{APP_UNIQUE}'",
    ).get("value", [])
    body = {
        "name": APP_NAME,
        "uniquename": APP_UNIQUE,
        "description": "Six-agent LSEG corporate and financial intelligence workspace.",
        "clienttype": 4,
        "navigationtype": 0,
        "url": APP_UNIQUE,
        "webresourceid": "953b9fac-1e5e-e611-80d6-00155ded156f",
        "formfactor": 1,
    }
    if rows:
        app_id = rows[0]["appmoduleid"]
        dv.api("PATCH", f"/appmodules({app_id})", body, headers=H)
        return app_id
    row = dv.api(
        "POST",
        "/appmodules",
        {
            **body,
            "appmoduleidunique": str(uuid.uuid4()),
        },
        headers={"Prefer": "return=representation"},
    )
    return row["appmoduleid"]


def ensure_sitemap() -> str:
    rows = dv.api(
        "GET",
        f"/sitemaps?$select=sitemapid&$filter=sitemapnameunique eq '{SITEMAP_UNIQUE}'",
    ).get("value", [])
    body = {
        "sitemapname": APP_NAME,
        "sitemapnameunique": SITEMAP_UNIQUE,
        "sitemapxml": SITEMAP_XML,
    }
    if rows:
        sitemap_id = rows[0]["sitemapid"]
        dv.api("PATCH", f"/sitemaps({sitemap_id})", body, headers=H)
        return sitemap_id
    row = dv.api(
        "POST",
        "/sitemaps",
        body,
        headers={**H, "Prefer": "return=representation"},
    )
    return row["sitemapid"]


def add_solution_component(component_id: str, component_type: int) -> None:
    try:
        dv.api(
            "POST",
            "/AddSolutionComponent",
            {
                "ComponentId": component_id,
                "ComponentType": component_type,
                "SolutionUniqueName": SOLUTION,
                "AddRequiredComponents": False,
                "DoNotIncludeSubcomponents": False,
            },
        )
    except Exception as exc:
        if "already exists" not in str(exc) and "0x8004F016" not in str(exc):
            raise


def add_app_component(
    app_id: str, app_unique_id: str, object_id: str, component_type: int
) -> None:
    existing = dv.api(
        "GET",
        "/appmodulecomponents?$select=appmodulecomponentid"
        f"&$filter=_appmoduleidunique_value eq {app_unique_id} and objectid eq {object_id} "
        f"and componenttype eq {component_type}",
    ).get("value", [])
    if existing:
        return
    dv.api(
        "POST",
        "/appmodulecomponents",
        {
            "objectid": object_id,
            "componenttype": component_type,
            "appmodulecomponentidunique": str(uuid.uuid4()),
            "appmoduleid@odata.bind": f"/appmodules({app_id})",
        },
        headers=H,
    )


def publish_app(app_id: str) -> None:
    try:
        dv.api("POST", "/PublishAppForUser", {"AppModuleId": app_id})
    except Exception as exc:
        if "Resource not found for the segment" not in str(exc):
            raise


def embed_in_rm_app(webresource_id: str, entity_id: str) -> tuple[str, str]:
    app = dv.api(
        "GET",
        f"/appmodules?$select=appmoduleid,appmoduleidunique,name"
        f"&$filter=uniquename eq '{HOST_APP_UNIQUE}'",
    )["value"][0]
    app_id = app["appmoduleid"]
    components = dv.api(
        "GET",
        "/appmodulecomponents?$select=objectid,componenttype"
        f"&$filter=_appmoduleidunique_value eq {app['appmoduleidunique']}",
    )["value"]
    sitemap_id = next(
        row["objectid"] for row in components if row["componenttype"] == 62
    )
    sitemap = dv.api("GET", f"/sitemaps({sitemap_id})?$select=sitemapxml")
    root = ET.fromstring(sitemap["sitemapxml"])
    existing = root.find(f".//SubArea[@Id='{SUBAREA_ID}']")
    if existing is None:
        area = root.find("./Area")
        if area is None:
            raise RuntimeError("RM CRM sitemap has no Area node")
        group = ET.Element(
            "Group",
            {"Id": "lseg_intelligence_group", "Title": "LSEG Intelligence"},
        )
        titles = ET.SubElement(group, "Titles")
        ET.SubElement(titles, "Title", {"LCID": "1033", "Title": "LSEG Intelligence"})
        subarea = ET.SubElement(
            group,
            "SubArea",
            {
                "Id": SUBAREA_ID,
                "Url": f"$webresource:{WEBRESOURCE_NAME}",
                "AvailableOffline": "false",
                "PassParams": "true",
            },
        )
        subarea_titles = ET.SubElement(subarea, "Titles")
        ET.SubElement(
            subarea_titles,
            "Title",
            {"LCID": "1033", "Title": "LSEG Intelligence Hub"},
        )
        area.insert(1 if area.find("Titles") is not None else 0, group)
    else:
        existing.attrib["Url"] = f"$webresource:{WEBRESOURCE_NAME}"
    xml = ET.tostring(root, encoding="unicode", short_empty_elements=True)
    dv.api("PATCH", f"/sitemaps({sitemap_id})", {"sitemapxml": xml})
    publish_app(app_id)
    return app_id, sitemap_id


def verify(app_id: str, sitemap_id: str) -> None:
    app = dv.api(
        "GET",
        f"/appmodules({app_id})?$select=name,uniquename,statecode,statuscode",
    )
    sitemap = dv.api("GET", f"/sitemaps({sitemap_id})?$select=sitemapxml")
    components = dv.api(
        "GET",
        "/appmodulecomponents?$select=objectid,componenttype"
        f"&$filter=_appmoduleid_value eq {app_id}",
    ).get("value", [])
    types = {row["componenttype"] for row in components}
    if WEBRESOURCE_NAME not in sitemap["sitemapxml"] or not {1, 61, 62}.issubset(types):
        raise RuntimeError("LSEG app navigation or components are incomplete")
    print(
        f"Verified {app['name']} ({app_id}) with sitemap {sitemap_id} "
        "and Hub, table, and navigation components"
    )


def main() -> None:
    if dv.org_url().rstrip("/").lower() != EXPECTED_ORG:
        raise RuntimeError(f"Active environment is not PTA OCS: {dv.org_url()}")
    webresource_id = lookup_webresource(WEBRESOURCE_NAME)
    entity_id = dv.api(
        "GET",
        "/EntityDefinitions(LogicalName='lseg_intelligenceanalysis')?$select=MetadataId",
    )["MetadataId"]
    add_solution_component(webresource_id, 61)
    app_id, sitemap_id = embed_in_rm_app(webresource_id, entity_id)
    sitemap = dv.api("GET", f"/sitemaps({sitemap_id})?$select=sitemapxml")
    if SUBAREA_ID not in sitemap["sitemapxml"] or WEBRESOURCE_NAME not in sitemap["sitemapxml"]:
        raise RuntimeError("RM CRM navigation does not contain the LSEG Intelligence Hub")
    print(f"Verified LSEG Intelligence Hub navigation in RM CRM ({app_id})")
    print(f"APP_ID={app_id}")
    print(f"APP_URL={EXPECTED_ORG}/main.aspx?appid={app_id}")


if __name__ == "__main__":
    main()
