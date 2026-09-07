#!/usr/bin/env python3
"""Deploy the server-side six-agent orchestration cloud flow."""

from __future__ import annotations

import os

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import dv  # noqa: E402


EXPECTED_ORG = os.environ.get("DATAVERSE_URL", "").rstrip("/")
ENVIRONMENT_ID = os.environ.get("POWER_PLATFORM_ENVIRONMENT_ID", "")
SOLUTION = "lseg_BankableWalletIntelligence"
FLOW_NAME = "LSEG Intelligence Hub - Run Six Agents"
FLOW_UNIQUE = "lseg_IntelligenceHubRunSixAgents"
H = {"MSCRM.SolutionUniqueName": SOLUTION}

COPILOT_REFERENCE = {
    "logical": "lseg_CopilotStudio",
    "display": "LSEG Intelligence Hub - Copilot Studio",
    "connector": "/providers/Microsoft.PowerApps/apis/shared_microsoftcopilotstudio",
    "connection": "shared-microsoftcopi-54e257be-a4e6-45d6-95f5-deabc6f99627",
}
DATAVERSE_REFERENCE = {
    "logical": "lseg_Dataverse",
    "display": "LSEG Intelligence Hub - Dataverse",
    "connector": "/providers/Microsoft.PowerApps/apis/shared_commondataserviceforapps",
    "connection": "shared-commondataser-9e955513-e8c0-4fbe-b293-5b777f5b06ef",
}

AGENTS = [
    {
        "key": "Orchestrator",
        "schema": "lseg_RMOrchestrator",
        "status": "lseg_orchestratorstatus",
        "result": "lseg_orchestratorresult",
        "prompt": (
            "Create a current executive intelligence view for {company}{identifiers}. "
            "Use LSEG data and clearly distinguish facts from hypotheses. Return exactly one valid JSON "
            "object with no markdown or code fences using this schema: "
            '{"summary":"string","latestPrice":"string","momentum":"string","riskScore":0,'
            '"risks":["string"],"opportunities":["string"],"trades":["string"],'
            '"questions":["string"],"wallet":[0,0,0,0],"tradeSummary":"string",'
            '"summarySignals":{"changed":["string"],"growth":["string"],"attention":["string"]},'
            '"relationshipStrength":{"score":0,"change":"string"},'
            '"walletOpportunity":{"value":"string","change":"string"},'
            '"priceAdvantage":{"value":"string","context":"string"},'
            '"tradeFlowGrowth":{"value":"string","period":"string"},'
            '"financials":[{"label":"string","value":"string","change":"string"}],'
            '"financialTrend":[0,0,0,0,0,0,0,0],'
            '"tradeRoutes":[{"label":"string","share":"string"}],'
            '"nextBestActions":[{"title":"string","detail":"string","type":"opportunity|task",'
            '"priority":"High|Medium|Low","estimatedValue":0,"dueDays":0}],'
            '"evidence":[{"fact":"string","source":"named LSEG dataset or Reuters","period":"string"}],'
            '"confidence":"High|Medium|Low","dataGaps":["string"]}. '
            "Wallet values are evidence-based 0-100 opportunity indicators for Lending, Cash, Trade, and Markets. "
            "Financial trend points must be normalized 0-100 values backed by a consistent reported metric and period. "
            "Classify revenue-generating recommendations as opportunity and review, validation, or monitoring work as task. "
            "Use null, an empty string, or an empty array when evidence does not support a field; never invent precision. "
            "Keep KPI fields short; put detailed reasoning and traceable source context in evidence."
        ),
    },
    {
        "key": "Wallet",
        "schema": "lseg_BankableWallet",
        "status": "lseg_walletstatus",
        "result": "lseg_walletresult",
        "prompt": (
            "Analyze the bankable wallet for {company}{identifiers}. Use LSEG evidence. "
            "Return a concise executive brief covering wallet ranges, lending, cash, trade, markets, "
            "assumptions, gaps, confidence, and three RM actions. Do not invent internal bank share. "
            "For every material conclusion label FACT, HYPOTHESIS, or DATA GAP and name the LSEG dataset, "
            "Reuters item, period, currency, or instrument used. Make the reasoning traceable."
        ),
    },
    {
        "key": "Pricing",
        "schema": "lseg_DynamicPricing",
        "status": "lseg_pricingstatus",
        "result": "lseg_pricingresult",
        "prompt": (
            "Prepare non-binding dynamic pricing intelligence for {company}{identifiers}. "
            "Use LSEG market and company evidence. Explain benchmarks, widening and tightening drivers, "
            "relationship value, sensitivities, missing internal inputs, and approval requirements. "
            "For every material conclusion label FACT, HYPOTHESIS, or DATA GAP and name the LSEG dataset, "
            "Reuters item, period, currency, or instrument used. Make the pricing logic traceable."
        ),
    },
    {
        "key": "Risk",
        "schema": "lseg_CreditRisk",
        "status": "lseg_riskstatus",
        "result": "lseg_riskresult",
        "prompt": (
            "Create an external credit and risk intelligence brief for {company}{identifiers}. "
            "Use LSEG evidence for financial, market, ownership, governance, sector, country, news, and event "
            "signals. Rank early warnings and recommend monitoring actions without assigning an internal grade. "
            "For every material conclusion label FACT, HYPOTHESIS, or DATA GAP and name the LSEG dataset, "
            "Reuters item, period, currency, or instrument used. Make each signal traceable."
        ),
    },
    {
        "key": "AccountPlan",
        "schema": "lseg_AccountPlanning",
        "status": "lseg_accountplanstatus",
        "result": "lseg_accountplanresult",
        "prompt": (
            "Build an evidence-based account plan for {company}{identifiers}. Use LSEG "
            "intelligence. Include strategic priorities, validated stakeholder hypotheses, opportunity themes, "
            "talking points, discovery questions, objections, and a measurable 30/60/90-day RM plan. "
            "For every material conclusion label FACT, HYPOTHESIS, or DATA GAP and name the LSEG dataset, "
            "Reuters item, period, currency, or instrument used. Tie each action to its evidence."
        ),
    },
    {
        "key": "Trade",
        "schema": "lseg_TradeIntelligence",
        "status": "lseg_tradestatus",
        "result": "lseg_traderesult",
        "prompt": (
            "Analyze trade and transaction-banking opportunities for {company}{identifiers}. "
            "Use LSEG company, sector, commodity, market, and geographic evidence. Separate known facts from "
            "corridor hypotheses and cover working capital, guarantees, cash, supply-chain finance, and FX. "
            "For every material conclusion label FACT, HYPOTHESIS, or DATA GAP and name the LSEG dataset, "
            "Reuters item, period, currency, commodity, or instrument used. Make the reasoning traceable."
        ),
    },
]


def ensure_connection_reference(config: dict) -> str:
    rows = dv.api(
        "GET",
        "/connectionreferences?$select=connectionreferenceid,connectionid,connectorid"
        f"&$filter=connectionreferencelogicalname eq '{config['logical']}'",
    ).get("value", [])
    body = {
        "connectionreferencelogicalname": config["logical"],
        "connectionreferencedisplayname": config["display"],
        "connectorid": config["connector"],
        "connectionid": config["connection"],
    }
    if rows:
        row = rows[0]
        if row.get("connectionid") != config["connection"]:
            dv.api("PATCH", f"/connectionreferences({row['connectionreferenceid']})", body, headers=H)
        return row["connectionreferenceid"]
    row = dv.api(
        "POST",
        "/connectionreferences",
        body,
        headers={**H, "Prefer": "return=representation"},
    )
    return row["connectionreferenceid"]


def initialize_variables() -> dict:
    actions: dict = {}
    previous: str | None = None
    for agent in AGENTS:
        key = agent["key"]
        definitions = [
            (f"{key}ConversationId", "string", "@guid()"),
            (f"{key}Activities", "array", []),
            (f"{key}Action", "string", "continue"),
        ]
        for name, kind, value in definitions:
            action_name = f"Initialize_{name}"
            actions[action_name] = {
                "type": "InitializeVariable",
                "inputs": {"variables": [{"name": name, "type": kind, "value": value}]},
                "runAfter": {} if previous is None else {previous: ["Succeeded"]},
            }
            previous = action_name
    actions["Mark_All_Agents_Running"] = {
        "type": "OpenApiConnection",
        "runAfter": {previous: ["Succeeded"]},
        "inputs": {
            "host": {
                "apiId": DATAVERSE_REFERENCE["connector"],
                "connectionName": "shared_commondataserviceforapps",
                "operationId": "UpdateRecord",
            },
            "parameters": {
                "entityName": "lseg_intelligenceanalysises",
                "recordId": "@triggerOutputs()?['body/lseg_intelligenceanalysisid']",
                "item/lseg_status": 100000001,
                **{f"item/{agent['status']}": 100000001 for agent in AGENTS},
            },
            "authentication": "@parameters('$authentication')",
        },
    }
    return actions


IDENTIFIERS_EXPRESSION = (
    "@{if(empty(coalesce(triggerOutputs()?['body/lseg_lei'],'')),'',"
    "concat(', LEI ',triggerOutputs()?['body/lseg_lei']))}"
    "@{if(empty(coalesce(triggerOutputs()?['body/lseg_country'],'')),'',"
    "concat(', country ',triggerOutputs()?['body/lseg_country']))}"
)


RESOLUTION_GUIDANCE = (
    " The company name is entered free-text by the user and may be informal, abbreviated, "
    "or misspelled. Resolve it yourself to the most likely real-world legal entity, state "
    "the resolved entity you analyzed, and if the name is genuinely ambiguous pick the most "
    "prominent match and flag the ambiguity as a data gap."
)


def agent_prompt(agent: dict) -> str:
    return (
        agent["prompt"]
        .replace("{company}", "@{triggerOutputs()?['body/lseg_companyname']}")
        .replace("{identifiers}", IDENTIFIERS_EXPRESSION)
        .replace("{lei}", "@{triggerOutputs()?['body/lseg_lei']}")
        .replace("{country}", "@{triggerOutputs()?['body/lseg_country']}")
        + RESOLUTION_GUIDANCE
    )


def parse_action(source: str, run_after: dict) -> dict:
    return {
        "type": "ParseJson",
        "runAfter": run_after,
        "inputs": {
            "content": f"@outputs('{source}').body",
            "schema": {
                "type": "object",
                "properties": {
                    "activities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "id": {"type": "string"},
                                "name": {"type": "string"},
                                "textFormat": {"type": "string"},
                                "text": {"type": "string"},
                                "timestamp": {"type": "string"},
                            },
                        },
                    },
                    "action": {"type": "string"},
                },
            },
        },
    }


def agent_branch(agent: dict) -> dict:
    key = agent["key"]
    start = f"{key}_Start"
    parse_start = f"{key}_Parse_Start"
    set_activities = f"{key}_Set_Activities"
    set_action = f"{key}_Set_Action"
    until = f"{key}_Wait_For_Completion"
    continue_name = f"{key}_Continue"
    parse_continue = f"{key}_Parse_Continue"
    set_continue_activities = f"{key}_Set_Continue_Activities"
    set_continue_action = f"{key}_Set_Continue_Action"
    update = f"{key}_Save_Result"
    activity = {
        "attachments": [],
        "channelData": {"attachmentSizes": []},
        "text": agent_prompt(agent),
        "textFormat": "plain",
        "type": "message",
        "channelId": "pva-autonomous",
    }
    return {
        start: {
            "type": "OpenApiConnection",
            "runAfter": {"Mark_All_Agents_Running": ["Succeeded"]},
            "inputs": {
                "parameters": {
                    "Copilot": agent["schema"],
                    "ConversationId": f"@variables('{key}ConversationId')",
                    "body": {"activity": activity},
                },
                "host": {
                    "apiId": COPILOT_REFERENCE["connector"],
                    "connectionName": "shared_microsoftcopilotstudio",
                    "operationId": "ExecuteDataverseCopilotToStart",
                },
            },
        },
        parse_start: parse_action(start, {start: ["Succeeded"]}),
        set_activities: {
            "type": "SetVariable",
            "runAfter": {parse_start: ["Succeeded"]},
            "inputs": {
                "name": f"{key}Activities",
                "value": f"@body('{parse_start}')?['activities']",
            },
        },
        set_action: {
            "type": "SetVariable",
            "runAfter": {set_activities: ["Succeeded"]},
            "inputs": {
                "name": f"{key}Action",
                "value": f"@body('{parse_start}')?['action']",
            },
        },
        update: {
            "type": "OpenApiConnection",
            "runAfter": {set_action: ["Succeeded"]},
            "inputs": {
                "host": {
                    "apiId": DATAVERSE_REFERENCE["connector"],
                    "connectionName": "shared_commondataserviceforapps",
                    "operationId": "UpdateRecord",
                },
                "parameters": {
                    "entityName": "lseg_intelligenceanalysises",
                    "recordId": "@triggerOutputs()?['body/lseg_intelligenceanalysisid']",
                    f"item/{agent['status']}": 100000002,
                    f"item/{agent['result']}": (
                        "@string("
                        "setProperty("
                        "setProperty("
                        "json('{}'), "
                        f"'conversationId', variables('{key}ConversationId')), "
                        f"'activities', variables('{key}Activities'))"
                        ")"
                    ),
                },
                "authentication": "@parameters('$authentication')",
            },
        },
    }


def build_clientdata() -> str:
    actions = initialize_variables()
    for agent in AGENTS:
        actions.update(agent_branch(agent))
    completed_actions = {f"{agent['key']}_Save_Result": ["Succeeded"] for agent in AGENTS}
    actions["Complete_Analysis"] = {
        "type": "OpenApiConnection",
        "runAfter": completed_actions,
        "inputs": {
            "host": {
                "apiId": DATAVERSE_REFERENCE["connector"],
                "connectionName": "shared_commondataserviceforapps",
                "operationId": "UpdateRecord",
            },
            "parameters": {
                "entityName": "lseg_intelligenceanalysises",
                "recordId": "@triggerOutputs()?['body/lseg_intelligenceanalysisid']",
                "item/lseg_status": 100000002,
                "item/lseg_resultjson": (
                    "@if(empty(variables('OrchestratorActivities')), '{}', "
                    "last(variables('OrchestratorActivities'))?['text'])"
                ),
            },
            "authentication": "@parameters('$authentication')",
        },
    }
    definition = {
        "$schema": (
            "https://schema.management.azure.com/providers/Microsoft.Logic/"
            "schemas/2016-06-01/workflowdefinition.json#"
        ),
        "contentVersion": "1.0.0.0",
        "parameters": {
            "$authentication": {"defaultValue": {}, "type": "SecureObject"},
            "$connections": {"defaultValue": {}, "type": "Object"},
        },
        "triggers": {
            "When_an_analysis_is_created": {
                "type": "OpenApiConnectionWebhook",
                "inputs": {
                    "host": {
                        "apiId": DATAVERSE_REFERENCE["connector"],
                        "connectionName": "shared_commondataserviceforapps",
                        "operationId": "SubscribeWebhookTrigger",
                    },
                    "parameters": {
                        "subscriptionRequest/message": 1,
                        "subscriptionRequest/entityname": "lseg_intelligenceanalysis",
                        "subscriptionRequest/scope": 4,
                        "subscriptionRequest/runas": 1,
                    },
                    "authentication": "@parameters('$authentication')",
                },
            }
        },
        "actions": actions,
        "outputs": {},
    }
    data = {
        "schemaVersion": "1.0.0.0",
        "properties": {
            "definition": definition,
            "connectionReferences": {
                "shared_microsoftcopilotstudio": {
                    "runtimeSource": "embedded",
                    "connection": {
                        "name": COPILOT_REFERENCE["connection"],
                        "connectionReferenceLogicalName": COPILOT_REFERENCE["logical"],
                    },
                    "api": {"name": "shared_microsoftcopilotstudio"},
                },
                "shared_commondataserviceforapps": {
                    "runtimeSource": "embedded",
                    "connection": {
                        "name": DATAVERSE_REFERENCE["connection"],
                        "connectionReferenceLogicalName": DATAVERSE_REFERENCE["logical"],
                    },
                    "api": {"name": "shared_commondataserviceforapps"},
                },
            },
        },
    }
    return json.dumps(data, separators=(",", ":"))


def upsert_flow() -> str:
    existing = dv.api(
        "GET",
        f"/workflows?$select=workflowid,statecode&$filter=name eq '{FLOW_NAME}' and category eq 5",
    ).get("value", [])
    body = {
        "name": FLOW_NAME,
        "uniquename": FLOW_UNIQUE,
        "category": 5,
        "type": 1,
        "primaryentity": "none",
        "runas": 1,
        "clientdata": build_clientdata(),
    }
    if existing:
        workflow_id = existing[0]["workflowid"]
        if existing[0]["statecode"] == 1:
            dv.api(
                "PATCH",
                f"/workflows({workflow_id})",
                {"statecode": 0, "statuscode": 1},
            )
        dv.api("PATCH", f"/workflows({workflow_id})", body, headers=H)
    else:
        me = dv.api("GET", "/WhoAmI")["UserId"]
        row = dv.api(
            "POST",
            "/workflows",
            {
                **body,
                "statecode": 0,
                "statuscode": 1,
                "ownerid@odata.bind": f"/systemusers({me})",
            },
            headers={**H, "Prefer": "return=representation"},
        )
        workflow_id = row["workflowid"]
    dv.api(
        "PATCH",
        f"/workflows({workflow_id})",
        {"statecode": 1, "statuscode": 2},
    )
    return workflow_id


def verify(workflow_id: str) -> None:
    row = dv.api(
        "GET",
        f"/workflows({workflow_id})?$select=name,statecode,statuscode,clientdata",
    )
    data = json.loads(row["clientdata"])
    actions = data["properties"]["definition"]["actions"]
    for agent in AGENTS:
        if f"{agent['key']}_Start" not in actions or f"{agent['key']}_Save_Result" not in actions:
            raise RuntimeError(f"Missing flow branch for {agent['key']}")
        saved_value = actions[f"{agent['key']}_Save_Result"]["inputs"]["parameters"][
            f"item/{agent['result']}"
        ]
        if "conversationId" not in saved_value or "activities" not in saved_value:
            raise RuntimeError(f"Conversation history is not persisted for {agent['key']}")
    if row["statecode"] != 1 or row["statuscode"] != 2:
        raise RuntimeError("Orchestration flow is not active")
    print(
        f"Verified active flow {row['name']} ({workflow_id}) with "
        f"{len(AGENTS)} Copilot Studio branches"
    )


def main() -> None:
    if dv.org_url().rstrip("/").lower() != EXPECTED_ORG:
        raise RuntimeError(f"Active environment is not PTA OCS: {dv.org_url()}")
    ensure_connection_reference(COPILOT_REFERENCE)
    ensure_connection_reference(DATAVERSE_REFERENCE)
    workflow_id = upsert_flow()
    verify(workflow_id)
    print(f"FLOW_ID={workflow_id}")


if __name__ == "__main__":
    main()
