# goodbot Fork Codebase Overview

## What This Repository Is

`goodbot` is an enterprise-focused downstream fork of upstream `HKUDS/nanobot`.

- User-facing CLI command: `goodbot`
- Internal Python package/layout: `nanobot/` (kept for upstream merge viability)
- Primary goal: keep upstream compatibility while enforcing safer enterprise defaults

## Current Fork Focus

Current implementation emphasizes:

- CLI-first operation with explicit runtime profile guards
- OpenAI model route with optional local Codex CLI auth (`useCodexCli`)
- Default-deny tooling/channel posture in enterprise profile
- Additive Teams channel path (stub and live webhook modes)

## High-Level Architecture

Core runtime components:

1. `nanobot/cli/commands.py`
- Typer CLI commands (`onboard`, `agent`, `gateway`, `status`, `cron`, `channels`).
- Runtime profile enforcement for `agent` and `gateway`.

2. `nanobot/config/`
- Pydantic schema and JSON load/save with camelCase <-> snake_case conversion.
- Profile validation in `config/profile.py` (`enterprise_minimal`).

3. `nanobot/bus/`
- `MessageBus` provides async inbound/outbound queues.
- Channel adapters publish `InboundMessage`; agent publishes `OutboundMessage`.

4. `nanobot/channels/`
- Shared `BaseChannel` interface + `ChannelManager`.
- Supported channels include WhatsApp, Telegram, Discord, Slack, Email, Teams, and others.
- Teams (`channels/teams.py`) supports:
  - `stub` mode (deterministic feasibility/testing)
  - `botframework_webhook` live mode (webhook ingress + outbound replies)

5. `nanobot/agent/`
- `AgentLoop` orchestrates context building, provider calls, and tool iteration.
- Tool policy gates are applied at registration and execution paths.

6. `nanobot/providers/`
- `LiteLLMProvider` for API-key-based providers.
- `CodexCLIProvider` path for `openai/*` models when `providers.openai.useCodexCli=true`.

7. `nanobot/session/`, `nanobot/cron/`, `nanobot/heartbeat/`
- Session persistence, scheduled jobs, and periodic heartbeat execution.

8. `bridge/` (Node.js)
- WhatsApp bridge transport used by the WhatsApp channel adapter.

## Main Execution Flows

### Direct CLI (`goodbot agent`)

1. Load config and enforce runtime profile.
2. Resolve provider route (LiteLLM or Codex CLI path).
3. Process message through `AgentLoop`.
4. Persist session/history updates.

### Gateway (`goodbot gateway`)

1. Load config, enforce runtime profile, create bus/agent/services.
2. Start enabled channels in `ChannelManager`.
3. Inbound channel events are normalized into `InboundMessage`.
4. Agent processes and emits `OutboundMessage`.
5. Dispatcher routes outbound messages back through channel adapters.

## Security and Policy Model (Fork)

- Enterprise profile is CLI-first and enforces explicit channel approval.
- Default channel posture is deny-by-default unless allowlists/policies permit.
- High-risk tools are blocked by default and require explicit opt-in.
- Web and filesystem restrictions are designed to reduce SSRF/path-escape risk.

Detailed controls live in:

- `plan/security-risk-register.md`
- `plan/security-policy-matrix.md`
- `FORK-DIFFERENCES.md`

## State and Persistence

Compatibility paths are currently retained:

- Config: `~/.nanobot/config.json`
- Workspace default: `~/.nanobot/workspace`
- Sessions: `~/.nanobot/sessions/*.jsonl`
- Cron jobs: `~/.nanobot/cron/jobs.json`
- Media/download cache paths under `~/.nanobot/`

## Extensibility Points

- Add/adjust provider: `nanobot/providers/registry.py` + `nanobot/config/schema.py`
- Add/adjust channel: implement `BaseChannel`, wire through `nanobot/channels/manager.py`
- Add/adjust tools: register and gate through agent/tool policy paths
- Add enterprise divergence note: update `FORK-DIFFERENCES.md` in the same PR

## Operational References

- Product/fork overview: `README.md`
- Execution plan: `plan/enterprise-adaptation-feasibility.md`
- Fork divergence register: `FORK-DIFFERENCES.md`
