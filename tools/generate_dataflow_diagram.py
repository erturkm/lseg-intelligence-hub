import os
import base64
import subprocess
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "lseg-agent-output-dataflow.png"
ENDPOINT = os.environ.get("AZURE_OPENAI_IMAGE_ENDPOINT", "")

PROMPT = """
Create a precise, technical data-flow diagram for engineers. 16:9 landscape.
Clean, airy, highly legible. This is a developer reference chart, not marketing.

Title: LSEG Intelligence Hub - How six agent outputs reach the UI
Subtitle: Dataverse columns, parser functions and DOM element IDs

Layout as FOUR labelled horizontal rows, flowing top to bottom.

ROW 1 - SIX AGENTS (six small rounded tiles side by side, purple):
"RM Orchestrator", "Bankable Wallet", "Dynamic Pricing",
"Credit & Risk", "Account Planning", "Trade Intelligence".
Put a small tag under the first tile reading "returns JSON".
Put one shared small tag under the other five reading "return prose".

ROW 2 - DATAVERSE COLUMNS (blue database row, monospace style labels):
Six column chips, one under each agent, labelled exactly:
"lseg_orchestratorresult", "lseg_walletresult", "lseg_pricingresult",
"lseg_riskresult", "lseg_accountplanresult", "lseg_traderesult".
To the right, slightly separated and highlighted in a stronger blue,
one extra chip labelled "lseg_resultjson"
with a small caption beneath: "= last Orchestrator activity text".
Draw an arrow from the RM Orchestrator column chip across to lseg_resultjson.

ROW 3 - CLIENT PARSERS (teal, monospace function names in rounded boxes):
Left box: "parseAgentJson()" with caption "strips code fences, brace-slice fallback".
Middle box: "normalizeAgentPayload()" with caption "conversationId + activities".
Right box: "classifyAgentOutput()" with caption
"regex mining: FACT / HYPOTHESIS / DATA GAP".
Far right box: "extractTimedActions()" with caption "30D / 60D / 90D".
Arrow from lseg_resultjson down into parseAgentJson.
Arrows from the five prose columns down into classifyAgentOutput.

ROW 4 - UI ELEMENTS (dark navy outlined chips, monospace IDs), two groups:
Group A labelled "from JSON - data.*":
chips "executiveInsight", "kpiPrice", "kpiRisk", "riskScore",
"walletBars", "tradeChips", "evidence", "nextBestActions".
Group B labelled "from prose - state.agentResults.*":
chips "walletHeadline", "riskHeadline", "pricingHeadline",
"accountHeadline", "actionPlan", "pricingSignals".
Arrows from parseAgentJson into Group A, and from
classifyAgentOutput / extractTimedActions into Group B.

On the right-hand edge add a narrow vertical callout panel titled
"JSON enforcement" containing three short stacked lines:
"1. prompt-only schema instruction",
"2. no structured output binding",
"3. defensive client parse + fallbacks".
Tint this panel pale amber to read as a caveat.

Visual style: Microsoft Fluent 2 technical diagram. White background,
dark navy text, purple for agents, blue for Dataverse, teal for parsers,
amber only for the caveat panel. Use monospace lettering for all
column names, function names and element IDs. Thin clean arrows.
Labels must be crisp, concise and correctly spelled.
No logos, no photographs, no robots, no 3D, no gradients, no clutter.
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
