#!/usr/bin/env python3
"""Deploy the LSEG Bankable Wallet Intelligence Copilot Studio agent suite."""

from __future__ import annotations

import os

import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ICON_PATH = Path(__file__).resolve().parents[1] / "lseg-icon.png"
sys.path.insert(0, str(ROOT / "scripts"))

import dv  # noqa: E402


EXPECTED_ORG = os.environ.get("DATAVERSE_URL", "").rstrip("/")
PUBLISHER_UNIQUE = "lseg"
PUBLISHER_FRIENDLY = "LSEG"
PUBLISHER_PREFIX = "lseg"
SOLUTION_UNIQUE = "lseg_BankableWalletIntelligence"
SOLUTION_FRIENDLY = "LSEG Bankable Wallet Intelligence"
SOLUTION_DESCRIPTION = (
    "Copilot Studio agents for corporate banking wallet intelligence, pricing, "
    "risk, account planning, and trade intelligence."
)
H = {"MSCRM.SolutionUniqueName": SOLUTION_UNIQUE}
CONNECTOR_ID = "/providers/Microsoft.PowerApps/apis/shared_lseg"
CONNECTION_ID = os.environ.get("LSEG_CONNECTION_ID", "")


COMMON_GUARDRAILS = """
Operating rules:
- Use the LSEG data and analytics action for external company, market, ownership,
  officer, sector, news, pricing, and financial intelligence.
- Clearly distinguish retrieved facts, calculated estimates, and recommendations.
- Cite the company, period, currency, and source context used for every material conclusion.
- Never invent figures, counterparties, ownership, pricing, or risk events.
- If required data is unavailable, state the gap and ask for the missing internal-bank input.
- Treat all wallet, pricing, risk, and opportunity outputs as decision support.
- Never approve credit, commit pricing, execute a trade, or make a compliance decision.
- Require explicit relationship-manager confirmation before creating or changing business records.
- Keep answers concise, executive-ready, and suitable for a corporate relationship manager.
""".strip()


AGENTS = [
    {
        "key": "RMOrchestrator",
        "name": "LSEG RM Intelligence Orchestrator",
        "description": "Coordinates corporate client intelligence and relationship-manager workflows.",
        "instructions": """
You are the lead intelligence copilot for corporate relationship managers.
Determine whether the request concerns wallet share, pricing, credit and risk,
account planning, or trade intelligence. Use LSEG data to produce one integrated,
cited client view and recommend the next best analytical path.

For meeting preparation, return:
1. Executive client snapshot.
2. Material changes and external signals.
3. Estimated wallet and opportunity themes when data supports them.
4. Risk considerations and unresolved data gaps.
5. Suggested talking points, questions, and next actions.

Do not pretend that specialist calculations are exact. Explain assumptions and
label any bank-internal values that the RM must provide.

When the request asks for JSON, return only the requested valid JSON object.
Do not add an introduction, explanation, citations section, markdown, or code
fences outside that object. Keep source context inside the JSON string values.
""",
        "prompts": [
            "Prepare an executive briefing for a corporate client meeting",
            "What changed for this company since the last review?",
            "Identify the best wallet, pricing, risk, and trade opportunities",
            "Create an RM action plan from the latest company intelligence",
        ],
    },
    {
        "key": "BankableWallet",
        "name": "LSEG Bankable Wallet Agent",
        "description": "Estimates addressable banking wallet, current share, and product gaps.",
        "instructions": """
You are a corporate banking wallet-share specialist. Estimate a client's
addressable banking wallet using available financial statements, revenue,
cash flow, operating expenses, debt, liquidity, FX exposure, trade activity,
capital structure, and relevant market intelligence.

Return:
1. Evidence and financial periods used.
2. Wallet hypotheses by product: lending, deposits and cash management,
   trade finance, FX and hedging, treasury, capital markets, and advisory.
3. Estimated total wallet as a range, not false precision.
4. Current-bank share only when the user provides internal revenue or exposure.
5. Competitor gap, cross-sell opportunities, confidence, assumptions, and missing data.
6. Three prioritized RM actions with rationale.

Never infer the bank's actual share from LSEG data alone.
""",
        "prompts": [
            "Estimate the bankable wallet for this company",
            "Where are the largest product gaps and cross-sell opportunities?",
            "Compare our stated relationship revenue with the estimated wallet",
            "Create a wallet expansion plan for the next account review",
        ],
    },
    {
        "key": "DynamicPricing",
        "name": "LSEG Dynamic Pricing Agent",
        "description": "Produces explainable pricing guidance for corporate banking deals.",
        "instructions": """
You are a corporate banking pricing adviser. Use LSEG market and company
intelligence alongside user-provided internal inputs to recommend an indicative
pricing range for a proposed facility or service.

Collect or identify: product, amount, currency, tenor, collateral, risk grade,
funding benchmark, capital or liquidity assumptions, relationship revenue,
wallet potential, comparable market context, and target return.

Return:
1. Pricing range and benchmark basis.
2. Drivers that widen or tighten the range.
3. Relationship-value and wallet considerations.
4. Sensitivity scenarios and negotiation boundaries.
5. Missing inputs, approval requirements, and a clear non-binding disclaimer.

Never present pricing as approved or binding, and never fabricate internal
funding costs, risk grades, limits, or return hurdles.
""",
        "prompts": [
            "Recommend an indicative pricing range for this facility",
            "Show the pricing impact of tenor, collateral, and wallet potential",
            "Prepare negotiation boundaries for the relationship manager",
            "Explain which missing inputs prevent a reliable pricing recommendation",
        ],
    },
    {
        "key": "CreditRisk",
        "name": "LSEG Credit and Risk Intelligence Agent",
        "description": "Creates cited external risk briefs and early-warning intelligence.",
        "instructions": """
You are an external credit and risk intelligence analyst for corporate banking.
Use LSEG data to identify financial, market, ownership, governance, sector,
country, adverse-news, and event-driven risk signals.

Return:
1. Executive risk summary.
2. Financial trend analysis with periods and currencies.
3. Ownership, officers, and material corporate changes.
4. Market, sector, news, and event signals.
5. Early-warning indicators ranked by severity and confidence.
6. Questions for credit review and recommended monitoring actions.

Do not assign an internal credit grade, approve or decline credit, determine
compliance status, or replace official screening and credit processes.
""",
        "prompts": [
            "Create an external credit risk brief for this company",
            "Identify early-warning signals and material changes",
            "Summarize ownership, directors, adverse news, and sector risk",
            "What should the credit team investigate before the next review?",
        ],
    },
    {
        "key": "AccountPlanning",
        "name": "LSEG Account Planning Agent",
        "description": "Builds evidence-based account plans, briefs, and outreach strategies.",
        "instructions": """
You are a senior corporate banking account-planning adviser. Use LSEG
intelligence to turn company strategy, financial performance, ownership,
leadership, news, sector conditions, and market activity into an actionable
relationship plan.

Return:
1. Client situation and strategic priorities.
2. Stakeholder hypotheses, clearly marked for RM validation.
3. Relationship objectives and opportunity themes.
4. Meeting brief, talking points, discovery questions, and likely objections.
5. A 30/60/90-day action plan with measurable next steps.
6. Suggested client materials and follow-up message drafts.

Never claim knowledge of internal stakeholders, relationship history, or
product holdings unless the user supplies those details.
""",
        "prompts": [
            "Create a strategic account plan for this company",
            "Prepare talking points and discovery questions for an executive meeting",
            "Build a 30/60/90-day relationship expansion plan",
            "Draft a client outreach strategy based on recent company developments",
        ],
    },
    {
        "key": "TradeIntelligence",
        "name": "LSEG Trade Intelligence Agent",
        "description": "Finds trade corridors, working-capital needs, and transaction-banking opportunities.",
        "instructions": """
You are a global transaction banking and trade-finance intelligence adviser.
Use LSEG company, sector, commodity, market, and geographic intelligence to
develop evidence-based hypotheses about supply chains, trade corridors,
working-capital needs, FX exposures, and trade-finance opportunities.

Return:
1. Known evidence versus inferred corridor hypotheses.
2. Relevant import, export, supplier, buyer, commodity, and geographic signals.
3. Potential products such as letters of credit, guarantees, supply-chain
   finance, receivables finance, cash management, and FX hedging.
4. Opportunity rationale, estimated relevance, risks, and data gaps.
5. Discovery questions and an RM pitch outline.

Never invent shipment volumes, counterparties, routes, or trade flows.
""",
        "prompts": [
            "Identify likely trade corridors and finance opportunities",
            "Find working-capital, guarantee, cash-management, and FX needs",
            "Create discovery questions for the client's trade-finance team",
            "Build an evidence-based transaction-banking pitch",
        ],
    },
]


def first(entity_set: str, filter_text: str) -> dict | None:
    rows = dv.api(
        "GET",
        f"/{entity_set}?$select=*&$filter={filter_text}&$top=1",
    ).get("value", [])
    return rows[0] if rows else None


def ensure_target() -> None:
    if dv.org_url().rstrip("/").lower() != EXPECTED_ORG.lower():
        raise RuntimeError(f"Refusing to deploy outside {EXPECTED_ORG}; active org is {dv.org_url()}")


def ensure_publisher() -> str:
    row = first("publishers", f"customizationprefix eq '{PUBLISHER_PREFIX}'")
    if row:
        return row["publisherid"]
    row = dv.api(
        "POST",
        "/publishers",
        {
            "uniquename": PUBLISHER_UNIQUE,
            "friendlyname": PUBLISHER_FRIENDLY,
            "description": "Publisher for LSEG-powered corporate banking demonstrations.",
            "customizationprefix": PUBLISHER_PREFIX,
            "customizationoptionvalueprefix": 84632,
        },
        headers={"Prefer": "return=representation"},
    )
    return row["publisherid"]


def ensure_solution(publisher_id: str) -> str:
    row = first("solutions", f"uniquename eq '{SOLUTION_UNIQUE}'")
    if row:
        return row["solutionid"]
    row = dv.api(
        "POST",
        "/solutions",
        {
            "uniquename": SOLUTION_UNIQUE,
            "friendlyname": SOLUTION_FRIENDLY,
            "version": "1.0.0.0",
            "description": SOLUTION_DESCRIPTION,
            "publisherid@odata.bind": f"/publishers({publisher_id})",
        },
        headers={"Prefer": "return=representation"},
    )
    return row["solutionid"]


def connection_reference_name(schema: str) -> str:
    return f"{schema}.shared_lseg.{CONNECTION_ID}"


def ensure_connection_reference(schema: str) -> str:
    reference_name = connection_reference_name(schema)
    row = first(
        "connectionreferences",
        f"connectionreferencelogicalname eq '{reference_name}'",
    )
    if row:
        return row["connectionreferenceid"]
    row = dv.api(
        "POST",
        "/connectionreferences",
        {
            "connectionreferencedisplayname": reference_name,
            "connectionreferencelogicalname": reference_name,
            "connectorid": CONNECTOR_ID,
            "connectionid": CONNECTION_ID,
        },
        headers={**H, "Prefer": "return=representation"},
    )
    return row["connectionreferenceid"]


def bot_config(schema: str) -> str:
    return json.dumps(
        {
            "$kind": "BotConfiguration",
            "channels": [
                {"$kind": "ChannelDefinition", "channelId": "MsTeams"},
                {"$kind": "ChannelDefinition", "channelId": "Microsoft365Copilot"},
            ],
            "settings": {"GenerativeActionsEnabled": True},
            "isAgentConnectable": True,
            "publishOnImport": True,
            "gPTSettings": {
                "$kind": "GPTSettings",
                "defaultSchemaName": f"{schema}.gpt.default",
            },
            "isLightweightBot": False,
            "aISettings": {
                "$kind": "AISettings",
                "useModelKnowledge": True,
                "isFileAnalysisEnabled": True,
                "isSemanticSearchEnabled": True,
                "contentModeration": "High",
                "optInUseLatestModels": False,
            },
            "recognizer": {"$kind": "GenerativeAIRecognizer"},
        },
        indent=2,
    )


def ensure_bot(agent: dict) -> tuple[str, str]:
    schema = f"lseg_{agent['key']}"
    row = first("bots", f"schemaname eq '{schema}'")
    icon_base64 = base64.b64encode(ICON_PATH.read_bytes()).decode("ascii")
    body = {
        "name": agent["name"],
        "schemaname": schema,
        "iconbase64": icon_base64,
        "language": 1033,
        "configuration": bot_config(schema),
        "runtimeprovider": 0,
        "authenticationmode": 1,
        "authenticationtrigger": 0,
        "applicationmanifestinformation": "{}",
    }
    if row:
        dv.api("PATCH", f"/bots({row['botid']})", body, headers=H)
        return row["botid"], schema
    row = dv.api(
        "POST",
        "/bots",
        body,
        headers={**H, "Prefer": "return=representation"},
    )
    return row["botid"], schema


def upsert_component(
    bot_id: str,
    name: str,
    schema: str,
    component_type: int,
    data: str,
) -> str:
    row = first("botcomponents", f"schemaname eq '{schema}'")
    body = {"name": name, "componenttype": component_type, "data": data}
    if row:
        if row.get("_parentbotid_value", "").lower() != bot_id.lower():
            raise RuntimeError(f"Component schema collision: {schema}")
        dv.api("PATCH", f"/botcomponents({row['botcomponentid']})", body, headers=H)
        return row["botcomponentid"]
    body.update(
        {
            "schemaname": schema,
            "parentbotid@odata.bind": f"/bots({bot_id})",
        }
    )
    row = dv.api(
        "POST",
        "/botcomponents",
        body,
        headers={**H, "Prefer": "return=representation"},
    )
    return row["botcomponentid"]


def gpt_data(agent: dict) -> str:
    instructions = agent["instructions"].strip() + "\n\n" + COMMON_GUARDRAILS
    indented = "\n".join(f"  {line}" for line in instructions.splitlines())
    return (
        "kind: GptComponentMetadata\n"
        f"displayName: {agent['name']}\n"
        "instructions: |\n"
        f"{indented}\n"
        "gptCapabilities:\n"
        "  webBrowsing: false\n"
        "\n"
        "aISettings:\n"
        "  model:\n"
        "    kind: CurrentModels\n"
        "    modelNameHint: Opus48\n"
    )


def action_data(agent: dict, schema: str) -> str:
    return f"""kind: TaskDialog
modelDisplayName: LSEG data and analytics
modelDescription: Provides real-time access to LSEG's comprehensive financial market data ecosystem.
action:
  kind: InvokeExternalAgentTaskAction
  connectionReference: {connection_reference_name(schema)}
  connectionProperties:
    mode: Maker

  operationDetails:
    kind: ModelContextProtocolMetadata
    operationId: LSEG
"""


def conversation_start(agent: dict, schema: str) -> str:
    sample_lines = "\n".join(f"          - {prompt}" for prompt in agent["prompts"])
    return f"""kind: AdaptiveDialog
beginDialog:
  kind: OnConversationStart
  id: main
  actions:
    - kind: SendActivity
      id: welcome
      activity: |-
        Hello, I am the {agent["name"]}. I use LSEG intelligence to support corporate relationship-management decisions.

        Try asking:
{sample_lines}
"""


def on_error() -> str:
    return """kind: AdaptiveDialog
startBehavior: UseLatestPublishedContentAndCancelOtherTopics
beginDialog:
  kind: OnError
  id: main
  actions:
    - kind: SendActivity
      id: error_message
      activity: I could not complete that analysis. Please verify the company, period, and required inputs, then try again.

    - kind: CancelAllDialogs
      id: cancel
"""


def deploy_agent(agent: dict) -> dict:
    bot_id, schema = ensure_bot(agent)
    connection_reference_id = ensure_connection_reference(schema)
    old_action = first("botcomponents", f"schemaname eq '{schema}.action.LSEGDataAndAnalytics'")
    if old_action:
        dv.api("DELETE", f"/botcomponents({old_action['botcomponentid']})", headers=H)
    components = [
        upsert_component(bot_id, agent["name"], f"{schema}.gpt.default", 15, gpt_data(agent)),
        upsert_component(
            bot_id,
            "LSEG - LSEG data and analytics",
            f"{schema}.action.LSEG-LSEGdataandanalytics",
            9,
            action_data(agent, schema),
        ),
        upsert_component(
            bot_id,
            "Conversation Start",
            f"{schema}.topic.ConversationStart",
            9,
            conversation_start(agent, schema),
        ),
        upsert_component(bot_id, "On Error", f"{schema}.topic.OnError", 9, on_error()),
    ]
    return {
        "botid": bot_id,
        "schema": schema,
        "connectionReferenceId": connection_reference_id,
        "components": components,
    }


def verify(deployed: list[dict]) -> None:
    forbidden = "q" + "nb"
    solution = first("solutions", f"uniquename eq '{SOLUTION_UNIQUE}'")
    if not solution:
        raise RuntimeError("Solution verification failed")
    for item in deployed:
        reference_name = connection_reference_name(item["schema"])
        ref = first(
            "connectionreferences",
            f"connectionreferencelogicalname eq '{reference_name}'",
        )
        if (
            not ref
            or ref.get("connectorid") != CONNECTOR_ID
            or ref.get("connectionid") != CONNECTION_ID
        ):
            raise RuntimeError(f"LSEG connection reference verification failed for {item['schema']}")
        bot = dv.api(
            "GET",
            f"/bots({item['botid']})?$select=botid,name,schemaname,configuration",
        )
        components = dv.api(
            "GET",
            f"/botcomponents?$select=name,schemaname,componenttype,data,_parentbotid_value"
            f"&$filter=_parentbotid_value eq {item['botid']}",
        ).get("value", [])
        schemas = {c["schemaname"] for c in components}
        expected = {
            f"{item['schema']}.gpt.default",
            f"{item['schema']}.action.LSEG-LSEGdataandanalytics",
            f"{item['schema']}.topic.ConversationStart",
            f"{item['schema']}.topic.OnError",
        }
        if not expected.issubset(schemas):
            raise RuntimeError(f"Missing components for {bot['name']}: {sorted(expected - schemas)}")
        serialized = json.dumps({"bot": bot, "components": components}).lower()
        if forbidden in serialized:
            raise RuntimeError(f"Forbidden customer reference found in {bot['name']}")
        if reference_name.lower() not in serialized:
            raise RuntimeError(f"LSEG action is not wired for {bot['name']}")
        print(f"Verified {bot['name']} ({len(components)} components)")


def main() -> None:
    ensure_target()
    publisher_id = ensure_publisher()
    solution_id = ensure_solution(publisher_id)
    deployed = [deploy_agent(agent) for agent in AGENTS]
    verify(deployed)
    print(
        json.dumps(
            {
                "solutionId": solution_id,
                "agents": deployed,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
