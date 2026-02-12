# Agent/Contributor Operating Guide

This file defines practical working rules for this fork. Keep it concise and execution-focused.

## Fork Intent and Merge Direction

- This repository is an enterprise-focused downstream fork of `HKUDS/nanobot`.
- Merge direction is from upstream into this fork.
- Enterprise-specific fork behavior is maintained here; upstream contribution is optional and case-by-case.
- User-facing CLI command is `goodbot`; internal package/layout remains `nanobot`.

## Required Git Workflow

- Never push directly to `main`.
- Always work on a feature branch and open a PR.
- Keep PRs focused and test-backed.
- Only the repository owner merges PRs.

## Path Privacy

- Do not commit machine-local absolute paths (for example `/Users/...`, `/home/...`, `C:\...`) to tracked files.
- Use repo-relative paths in docs, PR descriptions, comments, and commit messages.
- Before commit/PR, scan changes for leaked absolute paths and replace them.

## Testing (Docker-First)

- Preferred full validation:
  - `tests/test_docker.sh`
- Equivalent direct Docker pytest run:
  - `docker build -t nanobot-test .`
  - `docker run --rm --entrypoint /bin/sh -v "$(pwd)":/workspace -w /workspace nanobot-test -lc "uv pip install --system --no-cache -e '.[dev]' && pytest -q"`
- For small changes, run targeted tests first, then full suite before merge.

## Strategy for Inherited Features

- Default approach: keep upstream features in tree and restrict by policy/profile instead of trimming code aggressively.
- If touching inherited code paths, add lightweight regression tests for changed behavior.
- Avoid heavy integration scaffolding for channels/features intentionally disabled in enterprise profile unless they are being enabled.
- Large removals/refactors of inherited modules require explicit justification because they increase upstream sync conflict cost.

## Divergence Tracking

- Any intentional fork-vs-upstream behavior difference must be recorded in `FORK-DIFFERENCES.md` in the same PR.
- During each upstream sync PR, review and update `FORK-DIFFERENCES.md` as a required checklist item.

## Documentation Maintenance

- When architecture, runtime flow, channel wiring, or provider routing changes, update `docs/OVERVIEW.md` in the same PR.

## Reference Documents

- Product/repo overview: `README.md`
- Fork divergence register: `FORK-DIFFERENCES.md`
- Execution plan: `plan/enterprise-adaptation-feasibility.md`
- Security risks and controls:
  - `plan/security-risk-register.md`
  - `plan/security-policy-matrix.md`
