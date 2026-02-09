# Enterprise Inventory and Target Contract for `enterprise_minimal`

This document is the Milestone 1 artifact for `plan/enterprise-adaptation-feasibility.md`. It defines what should be kept, disabled by default, or removed later to adapt this fork for enterprise use while preserving upstream merge viability, where merge direction means pulling changes from `HKUDS/nanobot` into this fork (not contributing these enterprise-specific changes back upstream).

## Purpose

The immediate goal is to define a strict, auditable contract for an enterprise profile without deleting large portions of upstream-compatible code yet. This enables short feedback loops and conflict-aware iteration before irreversible divergence.

This inventory now works alongside `plan/security-risk-register.md`, which records concrete pre-adaptation security risks and their required mitigation sequencing.

## Baseline Evidence (2026-02-09)

All commands were run from the repository root (`<repo-root>`).

Initial test run before environment setup:

    pytest -q
    ModuleNotFoundError: No module named 'nanobot'

Environment setup and reproducible test run:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"
    pytest -q
    13 passed, 1 warning in 2.87s

CLI smoke checks:

    source .venv/bin/activate
    nanobot --help
    nanobot status

Observed result:

    Config: ~/.nanobot/config.json ✗
    Workspace: ~/.nanobot/workspace ✗

Interpretation: runtime boots from editable install and test suite is reproducible in `.venv`, but first-run config bootstrap is still required for interactive local usage.

## Inventory and Classification

### Runtime Core

Keep:
- `nanobot/agent/loop.py` as the core orchestration engine.
- `nanobot/bus/` message queue/event flow.
- `nanobot/session/` session persistence and history.
- `nanobot/cli/commands.py` direct CLI workflow (`nanobot agent`).

Disable by default:
- `nanobot/cli/commands.py` gateway mode for enterprise profile until provider/channel policy gates are in place.
- Background task paths tied to unrestricted tools (`spawn`, `cron`) until policy enforcement exists.

Remove later candidates:
- None in Milestone 1. Keep runtime core additive to reduce upstream conflicts.

### Providers

Keep:
- `openai` provider path as the only allowed backend for `enterprise_minimal`.
- Shared LiteLLM adapter in `nanobot/providers/litellm_provider.py`, with explicit enterprise validation in front of it.

Disable by default:
- All non-OpenAI providers currently declared in `nanobot/config/schema.py` and `nanobot/providers/registry.py`: `anthropic`, `openrouter`, `deepseek`, `groq`, `zhipu`, `dashscope`, `vllm`, `gemini`, `moonshot`, `aihubmix`.

Remove later candidates:
- Non-OpenAI provider config fields and registry entries only if the project accepts higher long-term upstream merge cost. For feasibility phase, keep code and enforce policy denial instead of deletion.

### Channels

Keep:
- CLI direct interaction (`nanobot agent`) as baseline enterprise entry point.
- Channel abstraction interfaces (`nanobot/channels/base.py`, `nanobot/channels/manager.py`) so Teams can be added without architectural rewrite.

Disable by default:
- All current external channels in enterprise profile: `telegram`, `whatsapp`, `discord`, `feishu`, `dingtalk`, `email`.

Remove later candidates:
- WhatsApp bridge stack (`bridge/`, `nanobot/channels/whatsapp.py`) after policy gates and upstream sync strategy are proven.
- Consumer/regional channels can be moved behind optional extras or split packages only after Teams path is validated.

Current gap:
- No Teams transport exists yet under `nanobot/channels/`; Teams is an additive Milestone 4 spike.

### Tools and Automation Surface

Keep:
- Tool framework and registry (`nanobot/agent/tools/base.py`, `nanobot/agent/tools/registry.py`) as extension mechanism.
- Read-only workspace navigation (`read_file`, `list_dir`) with stronger path controls in later milestone.

Disable by default:
- `exec` shell execution tool (`nanobot/agent/tools/shell.py`).
- File mutation tools (`write_file`, `edit_file`) until policy and audit rules are enforced.
- Network tools (`web_search`, `web_fetch`) unless explicitly approved by policy.
- Autonomous fan-out/scheduling tools (`spawn`, `cron`) until governance controls exist.
- Cross-channel dispatch tool (`message`) unless an approved enterprise channel is explicitly enabled.

Remove later candidates:
- None in Milestone 1. Keep tools available behind profile policies to avoid immediate fork drift.

Security note:
- `nanobot/agent/tools/filesystem.py` currently uses a prefix-string path check (`startswith`), which is weak and must be replaced with path ancestry checks in security hardening.
- `nanobot/agent/tools/shell.py` uses deny-patterns and should be treated as insufficient for enterprise default permissions.

### Dependency Surface

Keep:
- Core Python dependency set in `pyproject.toml` required for current runtime and tests.

Disable by default:
- Runtime use of channel-specific SDKs unless enterprise-approved channel is active.

Remove later candidates:
- Node.js bridge dependency footprint under `bridge/package.json` if WhatsApp is permanently out of scope.

## Enterprise Target Contract (`enterprise_minimal`)

### Allowed by Default

- Interaction mode: CLI direct only.
- Provider: OpenAI route only (ChatGPT/Codex model families selected via configured model string).
- Tools: read-only local inspection tools (`read_file`, `list_dir`) within approved workspace boundaries.
- Session persistence: enabled.

### Explicitly Optional (Off by Default)

- Microsoft Teams channel once Milestone 4 adapter exists and is explicitly enabled.
- Additional enterprise connectors (Microsoft 365/SharePoint, Jira, Confluence, Miro) only through explicit adapter registration and policy controls.

### Prohibited in `enterprise_minimal`

- Non-OpenAI provider selection.
- Consumer/regional channels (`telegram`, `whatsapp`, `discord`, `feishu`, `dingtalk`) and email channel auto-processing.
- Unrestricted command execution.
- Unrestricted file write/edit operations.
- Unapproved outbound web/network retrieval by tools.

## Upstream Compatibility Strategy from This Milestone

To keep merge cost bounded, Milestone 1 recommends policy-first constraints over immediate code deletion:

- Prefer additive profile checks in config and startup paths.
- Keep existing provider/channel/tool code paths present but unreachable in `enterprise_minimal` by policy.
- Delay physical module removal until Milestone 6 conflict rehearsal quantifies maintenance cost.
- Record each intentional divergence in `FORK-DIFFERENCES.md` in the same PR that introduces it.
- During upstream sync PRs, treat `FORK-DIFFERENCES.md` as a required audit checklist and update statuses.

This preserves optional rollback and reduces risk of broad conflicts when pulling upstream changes.

## Security Priority Override

Even though this inventory recommends additive, conflict-minimizing changes, execution order is constrained by security risk severity. Critical and high risks listed in `plan/security-risk-register.md` must be remediated or explicitly accepted with compensating controls before enabling enterprise channels or broader connector surfaces.

Execution note (2026-02-09): Milestone 2 security baseline gate has been implemented and validated; see closed statuses and evidence in `plan/security-risk-register.md` and defaults in `plan/security-policy-matrix.md`.
