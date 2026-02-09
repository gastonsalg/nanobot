# Security Policy Matrix (Milestone 2 Baseline)

This document defines enforced security defaults introduced during Milestone 2 and is paired with `plan/security-risk-register.md`.

## Scope

The matrix applies to the current baseline runtime before enterprise profile specialization. It intentionally favors default-safe behavior.

## Channel Inbound Policy

- Default behavior: deny unlisted senders when `allow_from` is empty.
- Explicit override: set `allow_unlisted_senders=true` per channel config to permit open access.
- Affected channels: WhatsApp, Telegram, Discord, Feishu, DingTalk, Email.

## Tool Execution Policy

The runtime now applies a central tool policy before registration and before execution.

Default blocked tools:

- `exec`
- `write_file`
- `edit_file`
- `web_search`
- `web_fetch`
- `spawn`
- `cron`

Default allowed tools:

- `read_file`
- `list_dir`
- `message` (if registered and context exists)

Configuration controls (`tools` section):

- `blocked_tools`: list of tool names denied by policy.
- `allowed_tools`: optional allowlist; when non-empty, only listed tools may run.
- `restrict_to_workspace`: defaults to `true`.

## Filesystem Boundary Policy

- Path checks use canonical ancestry validation (`Path.resolve` + `relative_to`) instead of string-prefix matching.
- Sibling path and traversal escapes outside the configured workspace are denied.

## Network Fetch Policy

- URL validation now blocks non-public targets (loopback, private, link-local, metadata endpoints).
- Hostnames that resolve to non-public IPs are denied.
- Only public HTTP/HTTPS targets pass validation.

## Bridge Command Policy (WhatsApp)

- Bridge server binds to `127.0.0.1` by default.
- Bridge startup requires `BRIDGE_TOKEN`.
- `send` commands must include a valid token.
- Python WhatsApp channel requires `channels.whatsapp.bridge_token` and includes it in send payloads.
- `nanobot channels login` auto-generates and stores a bridge token when missing.

## Secret Storage Policy

- Config directory permissions are enforced to `0700` (best effort on POSIX).
- Config file permissions are enforced to `0600` (best effort on POSIX).
- Session file permissions are enforced to `0600` and sessions directory to `0700` (best effort on POSIX).

## Remaining Decisions

- Whether `message` tool should be blocked by default in enterprise profile.
- Whether `web_search` should remain blocked or be selectively enabled with domain controls in enterprise mode.
