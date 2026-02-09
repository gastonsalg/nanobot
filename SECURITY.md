# Security Policy (Enterprise Fork)

## Scope

This document applies to this enterprise downstream fork repository (`<repo-root>`).

It does not define policy for upstream `HKUDS/nanobot`.

## Reporting Security Issues

Do not open public issues for vulnerabilities.

Use one of the following internal channels:

1. Your internal security ticketing process (preferred).
2. Private communication to repository maintainers if internal process is unavailable.

Include:

- Vulnerability description
- Reproduction steps
- Impact
- Proposed mitigation (if available)

## Current Security Baseline

This fork currently enforces:

- Default-deny channel sender policy when allow lists are empty.
- Tool policy gating with high-risk tools blocked by default.
- Workspace boundary enforcement for filesystem tools.
- SSRF protections in URL validation.
- Authenticated WhatsApp bridge command channel.
- Restrictive config/session file permissions on POSIX (best effort).

Reference documents:

- `plan/security-risk-register.md`
- `plan/security-policy-matrix.md`

## Operational Requirements

For enterprise deployment:

- Keep `~/.nanobot` ownership restricted to the runtime user.
- Keep secrets out of git and CI logs.
- Use environment-injected credentials where possible.
- Enable only approved channels and keep explicit allow lists.
- Keep blocked tool defaults unless risk acceptance is documented.

## Dependency Hygiene

Run regularly:

```bash
pip install -e ".[dev]"
pytest -q
```

For bridge dependencies:

```bash
cd bridge
npm audit
```

## Disclosure Expectations

For confirmed vulnerabilities in this fork:

- Triage quickly.
- Ship mitigation with tests where practical.
- Update the risk register and this policy when behavior changes.
