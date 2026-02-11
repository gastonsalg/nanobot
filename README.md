# goodbot Enterprise Fork

This repository is an enterprise-focused downstream fork of [HKUDS/nanobot](https://github.com/HKUDS/nanobot).

## Fork Intent

This fork exists to adapt upstream nanobot for internal enterprise use with stronger default security controls, a narrower runtime profile, and connector/channel decisions aligned with employer requirements.

The maintenance model is:

- Pull and merge improvements from upstream into this fork.
- Keep enterprise-specific changes in this fork.
- Do not assume enterprise-specific changes will be contributed back upstream.

## Current Status

The adaptation work is tracked in:

- `plan/enterprise-adaptation-feasibility.md`
- `plan/enterprise-inventory.md`
- `plan/security-risk-register.md`
- `plan/security-policy-matrix.md`
- `FORK-DIFFERENCES.md` (upstream vs fork divergence register)

As of 2026-02-09:

- Milestone 1 (inventory/contract) is complete.
- Milestone 2 (security baseline gate) is complete.
- Remaining work includes minimal enterprise profile completion, Teams feasibility, connector interfaces, and upstream sync rehearsal.

## Security Baseline Defaults

The fork now ships with default-safe behavior:

- Channel inbound access is default-deny when `allowFrom` is empty (unless explicitly overridden).
- High-risk tools are blocked by default (`exec`, file mutation, network fetch, spawn, cron).
- Tool access is policy-gated at registration and execution time.
- Filesystem workspace boundaries use canonical path ancestry checks.
- URL validation rejects private, loopback, link-local, and metadata targets.
- WhatsApp bridge command channel requires an auth token.
- Config and session files are saved with restrictive POSIX permissions (best effort).

## Quick Start (Local Development)

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

Initialize local config/workspace:

```bash
goodbot onboard
```

Run direct CLI mode:

```bash
goodbot agent -m "hello"
```

## Configuration Notes

Config lives at `~/.nanobot/config.json` (path intentionally kept for compatibility during fork evolution).

Important defaults in this fork:

- `tools.restrictToWorkspace` defaults to `true`.
- `tools.blockedTools` has a default deny list for high-risk tools.
- Channel configs include `allowUnlistedSenders` (default `false`).
- WhatsApp channel includes `bridgeToken` for bridge command authentication.

## Upstream Sync Practice

Recommended local setup:

```bash
git remote add upstream https://github.com/HKUDS/nanobot.git
git fetch upstream --tags
```

Then merge upstream changes into a dedicated sync branch in this fork and resolve conflicts there before promoting.

## Testing

Primary test command:

```bash
pytest -q
```

## License

This fork keeps the upstream MIT license. See `LICENSE`.
