# Security Risk Register (Pre-Adaptation Baseline)

This document records security findings discovered on 2026-02-09 before enterprise adaptation work proceeds. It is a gating artifact for planning and sequencing.

## Purpose

The purpose of this register is to prevent feature expansion from outpacing security controls. Each risk below must be tracked to closure or explicitly accepted with rationale.

## Risk 1: Untrusted inbound users can reach high-impact tools

Severity: Critical
Status: Closed (2026-02-09)

Why it matters:

If any external channel is enabled without an allow list, any sender can reach the agent. The agent exposes powerful tools by default, including shell execution and file mutation, and executes tool calls without a human approval step.

Evidence:

- `nanobot/channels/base.py` allows all senders when `allow_from` is empty.
- `nanobot/config/schema.py` channel `allow_from` defaults are empty lists.
- `nanobot/agent/loop.py` registers `exec`, `write_file`, `edit_file`, `web_fetch`, and executes tool calls directly.
- `nanobot/config/schema.py` sets `tools.restrict_to_workspace` default to `False`.

Required mitigation:

- Make enterprise profile default-deny for channels and users.
- Enforce tool policy gate before any tool execution.
- Disable high-risk tools by default in enterprise profile.

Closure evidence:

- `nanobot/channels/base.py` now denies unlisted senders by default unless `allow_unlisted_senders=true`.
- `nanobot/config/schema.py` now defaults channel `allow_unlisted_senders` to `False`, `tools.restrict_to_workspace` to `True`, and blocks high-risk tools by default via `tools.blocked_tools`.
- `nanobot/agent/loop.py` and `nanobot/agent/subagent.py` now enforce a centralized tool policy both at registration time and execution time.

Target milestone: Security Baseline Gate (Milestone 2).

## Risk 2: Filesystem workspace boundary check is bypassable

Severity: High
Status: Closed (2026-02-09)

Why it matters:

Workspace restriction uses string-prefix matching rather than path ancestry checks. Sibling paths can be treated as in-scope.

Evidence:

- `nanobot/agent/tools/filesystem.py` uses `str(resolved).startswith(str(allowed_dir.resolve()))`.
- Reproduction accepted `/tmp/workspace_evil/secret.txt` when allowed directory was `/tmp/workspace`.

Required mitigation:

- Replace prefix checks with canonical ancestry checks (`resolve` + strict parent relationship).
- Add tests for sibling-path and symlink escape cases.

Closure evidence:

- `nanobot/agent/tools/filesystem.py` now uses canonical ancestry validation (`relative_to`) instead of string-prefix checks.
- `tests/test_security_baseline.py` includes a sibling-prefix escape regression test.

Target milestone: Security Baseline Gate (Milestone 2).

## Risk 3: `web_fetch` allows SSRF to private and metadata endpoints

Severity: High
Status: Closed (2026-02-09)

Why it matters:

Current URL validation accepts private, loopback, and link-local IP targets. This can expose internal services or cloud instance metadata.

Evidence:

- `nanobot/agent/tools/web.py` validates only scheme and netloc.
- `web_fetch` executes arbitrary outbound requests after that validation.
- Reproduction accepted `http://127.0.0.1`, `http://10.0.0.5`, and `http://169.254.169.254`.

Required mitigation:

- Add host/IP policy validation that blocks loopback, RFC1918, link-local, and metadata endpoints.
- Resolve DNS and re-check target IP on connection.
- Gate network tools behind enterprise policy.

Closure evidence:

- `nanobot/agent/tools/web.py` now blocks loopback/private/link-local/metadata targets and rejects hostnames resolving to non-public IPs.
- `tests/test_security_baseline.py` includes direct-IP and hostname-resolution SSRF guard tests.

Target milestone: Security Baseline Gate (Milestone 2).

## Risk 4: WhatsApp bridge accepts unauthenticated WebSocket clients

Severity: High
Status: Closed (2026-02-09)

Why it matters:

Any client that can connect to the bridge socket can send commands that trigger outbound WhatsApp messages.

Evidence:

- `bridge/src/server.ts` starts a WebSocket server and accepts commands from connected clients without authentication.
- `bridge/src/server.ts` executes `send` commands directly via `wa.sendMessage`.

Required mitigation:

- Add transport authentication (shared secret or mTLS) and strict bind policy.
- Restrict by origin and optionally by local IPC transport.
- Disable bridge entirely in enterprise profile by default.

Closure evidence:

- `bridge/src/index.ts` now requires `BRIDGE_TOKEN` at startup.
- `bridge/src/server.ts` now validates command token before forwarding `send` requests.
- `nanobot/channels/whatsapp.py` now requires configured bridge token and attaches it to command payloads.
- `nanobot/cli/commands.py` (`channels login`) now generates and persists a bridge token when missing and passes it to bridge process env.

Target milestone: Security Baseline Gate (Milestone 2).

## Risk 5: Secrets stored in plaintext config without explicit restrictive file mode

Severity: Medium
Status: Closed (2026-02-09)

Why it matters:

API keys and passwords are persisted in local config and may be readable by other local users depending on environment umask and filesystem policy.

Evidence:

- `nanobot/config/loader.py` writes `~/.nanobot/config.json` with no explicit `chmod(0o600)`.

Required mitigation:

- Enforce secure permissions for config and data directories (`0700`) and config file (`0600`).
- Prefer environment-injected secrets for enterprise deployment.

Closure evidence:

- `nanobot/config/loader.py` now enforces best-effort POSIX permissions (`0700` dir, `0600` file) when saving config.
- `nanobot/session/manager.py` now enforces best-effort POSIX permissions on session dir/files.
- `tests/test_security_baseline.py` validates restrictive config file permissions on POSIX.

Target milestone: Security Baseline Gate (Milestone 2).

## Risk 6: Partial token disclosure in status output

Severity: Low
Status: Closed (2026-02-09)

Why it matters:

Printing token prefixes is unnecessary secret exposure in logs/screenshots.

Evidence:

- `nanobot/cli/commands.py` displays first 10 characters of Telegram token in channel status.

Required mitigation:

- Replace with redacted indicator only (present/absent).

Closure evidence:

- `nanobot/cli/commands.py` now reports Telegram token as configured/not configured without partial token preview.

Target milestone: Security Baseline Gate (Milestone 2).

## Prioritization Rule

No enterprise channel enablement, connector expansion, or Teams feasibility validation should proceed until Milestone 2 addresses Risks 1 through 4 and documents residual risk for Risks 5 and 6.

Gate result (2026-02-09):

- Milestone 2 security baseline gate passed with regression tests (`pytest -q` -> `20 passed`).
