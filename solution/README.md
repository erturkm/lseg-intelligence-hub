# Solution package

The exported Power Platform solution is available two ways:

- **In this folder** — `lseg_BankableWalletIntelligence_1_0_0_2.zip` (unmanaged, v1.0.0.2)
- **On the [Releases page](../../releases)** — tagged and versioned

## What the solution contains

- The `lseg_intelligenceanalysis` Dataverse table and its columns
- The six-agent orchestration cloud flow
- The six Copilot Studio agents and their MCP action bindings
- The `intelligence-hub` HTML web resource and supporting images
- Connection references for LSEG Data & Analytics, Dataverse, and Copilot Studio

## Importing

1. Download the zip from this folder or from Releases.
2. In [make.powerapps.com](https://make.powerapps.com), choose **Solutions → Import solution**.
3. When prompted, map each **connection reference** to a connection in your own tenant.
   The LSEG connection must be authenticated interactively with your own licensed credentials —
   no credentials are carried in the export.
4. After import, turn on the orchestration flow (imported flows arrive switched off).
5. Publish all customizations.

> [!NOTE]
> This export is **unmanaged**, intended for a development environment you plan to customise.
> For a downstream test or production environment, export a managed version from your own
> development environment instead.

> [!NOTE]
> The export captures the solution only. Environment-specific values such as the Dataverse URL,
> environment ID, and connection ID are supplied through environment variables when running the
> deployment scripts in `src/scripts/` — see the root [README](../README.md).
