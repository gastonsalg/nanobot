# Fork Differences Register

This file tracks intentional and known differences between this fork and upstream (`HKUDS/nanobot`).

Use this as the source of truth during upstream sync, PR review, and security audits to avoid repeatedly rediscovering expected divergences.

## Update Policy

Update this file in two situations:

1. Proactive update (required):
- When introducing a fork-specific behavior, policy, config default, or documentation change that intentionally diverges from upstream.
- Add or update the entry in the same PR as the code/docs change.

2. Sync-time audit update (required):
- During each upstream sync PR, review current entries and validate status.
- Add newly discovered divergences and mark stale ones as aligned/superseded.

## Entry Template

| Area | Upstream | Fork | Why | Intent | Review Trigger | Status |
| --- | --- | --- | --- | --- | --- | --- |
| channel auth defaults | empty allow list behavior | deny-by-default unless explicitly overridden | enterprise security baseline | permanent | every upstream sync | open |

## Current Differences

| Area | Upstream | Fork | Why | Intent | Review Trigger | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Channel inbound auth defaults | historically permissive when allow list was empty (varies by channel/version) | deny-by-default via `BaseChannel.is_allowed`; open access requires explicit opt-in (`allow_unlisted_senders=true`) | Milestone 2 security hardening | permanent | every upstream sync and channel-related PRs | open |
| QQ config docs wording | N/A (feature introduced via upstream sync) | `QQConfig.allow_from` inline comment currently says empty list means public access, but runtime is deny-by-default | documentation alignment pending | temporary | next PR touching QQ config/docs | open |
