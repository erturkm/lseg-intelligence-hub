import os
import base64
import subprocess
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "lseg-intelligence-hub-architecture.png"
ENDPOINT = os.environ.get("AZURE_OPENAI_IMAGE_ENDPOINT", "")

PROMPT = """
Create a premium, executive-level marketecture architecture diagram for a Microsoft
financial-services demonstration. 16:9 landscape, airy, highly legible.

Title: LSEG Intelligence Hub
Subtitle: Six Copilot Studio agents delivering live LSEG corporate intelligence inside Dynamics 365

Show a clear LEFT-TO-RIGHT flow in four labelled vertical bands:

BAND 1 - EXPERIENCE (Dynamics 365 Sales Hub):
A relationship manager at a browser. A card labelled "Intelligence Hub"
and beneath it "HTML web resource". A search box graphic with the caption
"Type any company name" and a small tag "free text - no directory lookup".

BAND 2 - DATA & ORCHESTRATION (Microsoft Dataverse):
A database cylinder labelled "Intelligence Analysis table" with small caption
"company name, status, six result columns".
Next to it a flow icon labelled "Power Automate" with caption
"Run Six Agents - parallel fan-out".
Draw a small circular arrow between the browser and the table labelled "polls status".

BAND 3 - AGENTS (Microsoft Copilot Studio):
Six equal rounded agent tiles arranged in two rows of three, all fed in parallel
from the Power Automate flow. Label them exactly:
"RM Intelligence Orchestrator", "Bankable Wallet", "Dynamic Pricing",
"Credit & Risk", "Account Planning", "Trade Intelligence".
Add a small band caption "generative orchestration - runs in parallel".

BAND 4 - EXTERNAL DATA (LSEG):
A connector/plug icon labelled "LSEG Data & Analytics" with a small badge "MCP".
Beneath it list four small tool chips:
"company fundamentals", "datastream pricing", "company news", "news search".

Draw arrows: browser to Dataverse table, table to Power Automate,
Power Automate fanning out to all six agent tiles, and all six agents
converging into the single LSEG MCP connector.
Then one clear return arrow from the agents back to the Dataverse table,
and from the table back to the browser, labelled "results".

At the bottom add a thin outcome strip with five small chips reading:
"RM AI summary", "bankable wallet", "risk signals", "next best actions",
"create opportunity or task in D365".

Visual style: polished Microsoft Fluent 2 marketecture. White and very pale warm
background. Dark navy text. Microsoft blue for Dynamics 365 and Dataverse.
Purple for Copilot Studio agents. Teal or deep green for LSEG external data.
Elegant flat line icons only. Crisp, correctly spelled, concise labels.
No logos, no photographs, no robots, no 3D, no browser chrome, no heavy gradients,
no decorative clutter, no invented product names.
""".strip()


def access_token() -> str:
    return subprocess.check_output(
        [
            "az",
            "account",
            "get-access-token",
            "--resource",
            "https://cognitiveservices.azure.com",
            "--query",
            "accessToken",
            "-o",
            "tsv",
        ],
        text=True,
    ).strip()


def main() -> None:
    response = requests.post(
        ENDPOINT,
        headers={
            "Authorization": f"Bearer {access_token()}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-image-2",
            "prompt": PROMPT,
            "size": "1536x1024",
            "quality": "high",
            "output_format": "png",
        },
        timeout=600,
    )
    response.raise_for_status()
    OUTPUT.write_bytes(base64.b64decode(response.json()["data"][0]["b64_json"]))
    print(f"{OUTPUT} ({OUTPUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
