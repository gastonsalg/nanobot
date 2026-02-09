# Enterprise Adaptation Feasibility for nanobot Fork

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan defines a research and experimentation track to determine whether this fork can become a secure, enterprise-focused assistant while still staying close enough to upstream (`HKUDS/nanobot`) to pull future core improvements.

## Purpose / Big Picture

After this work, we will know whether this fork can be narrowed to an enterprise-safe core that uses only ChatGPT/Codex as its AI backend, removes consumer messaging channels, and provides clean extension points for future Microsoft 365/SharePoint, Jira, Confluence, and Miro integrations. This plan now also evaluates Microsoft Teams as the first enterprise chat surface so we can verify whether users can chat with the assistant in Teams in addition to CLI. The visible outcome is a documented feasibility decision backed by runnable experiments, not assumptions. We will be able to run a minimal assistant profile locally, verify that unsafe or unnecessary features are disabled, test a Teams channel spike, and measure how difficult it is to keep syncing upstream.

## Progress

- [x] (2026-02-09 08:32Z) Read the `create-exec-plan` skill and canonical planning requirements.
- [x] (2026-02-09 08:32Z) Assumed default ExecPlan location `plan/` for this initial draft.
- [x] (2026-02-09 08:32Z) Authored initial feasibility and experimentation ExecPlan.
- [x] (2026-02-09 08:37Z) Revised plan to include explicit Microsoft Teams feasibility track.
- [x] (2026-02-09 08:39Z) Revised Teams scope to be additive with CLI (not a replacement).
- [x] (2026-02-09 08:45Z) Ran baseline `pytest -q` before environment setup and captured import failure (`ModuleNotFoundError: No module named 'nanobot'`).
- [x] (2026-02-09 08:49Z) Created `.venv`, installed editable package (`pip install -e ".[dev]"`), and reran tests (`13 passed, 1 warning`).
- [x] (2026-02-09 08:49Z) Ran CLI smoke checks (`nanobot --help`, `nanobot status`) and captured first-run config/workspace bootstrap status.
- [x] (2026-02-09 08:49Z) Authored `plan/enterprise-inventory.md` with explicit Keep/Disable-by-default/Remove-later contract.
- [x] (2026-02-09 09:06Z) Performed focused security audit and identified critical/high pre-adaptation risks.
- [x] (2026-02-09 09:06Z) Authored `plan/security-risk-register.md` with severity, evidence, and mitigation targets.
- [x] (2026-02-09 09:16Z) Implemented Milestone 2 security baseline controls across channel auth defaults, tool policy gating, filesystem boundary checks, SSRF validation, bridge auth, and secret file permissions.
- [x] (2026-02-09 09:16Z) Added Milestone 2 artifacts: `plan/security-policy-matrix.md` and updated `plan/security-risk-register.md` with closure status.
- [x] (2026-02-09 09:16Z) Ran full tests after security changes (`20 passed, 1 warning`).
- [x] (2026-02-09 08:49Z) Establish a reproducible local baseline environment (dependencies, tests, smoke run).
- [x] (2026-02-09 08:49Z) Complete Milestone 1 repository and risk inventory with explicit keep/remove candidates.
- [x] (2026-02-09 09:16Z) Complete Milestone 2 security baseline gate (close critical/high risks before channel expansion).
- [ ] Complete Milestone 3 minimal profile spike (CLI-first, OpenAI/Codex-only, Teams optional).
- [ ] Complete Milestone 4 Microsoft Teams channel feasibility spike.
- [ ] Complete Milestone 5 extension interface spike (Microsoft/Jira/Confluence/Miro adapter contracts with stubs).
- [ ] Complete Milestone 6 upstream sync rehearsal and conflict-cost measurement.
- [ ] Produce final feasibility recommendation and implementation roadmap.

## Surprises & Discoveries

- Observation: `session_key` is accepted by direct processing but not applied to session lookup.
  Evidence: `nanobot/agent/loop.py` defines `process_direct(..., session_key=...)` but builds `InboundMessage` from `channel/chat_id`, and `_process_message` uses `msg.session_key`.

- Observation: Version metadata is inconsistent.
  Evidence: `pyproject.toml` has `version = "0.1.3.post5"` while `nanobot/__init__.py` defines `__version__ = "0.1.0"`.

- Observation: Workspace path enforcement in filesystem tools is prefix-string based and should be treated as weak.
  Evidence: `nanobot/agent/tools/filesystem.py` uses `str(resolved).startswith(str(allowed_dir.resolve()))`.

- Observation: Current test suite focuses on selected areas and does not provide broad behavioral coverage for core orchestration and provider/channel matrix.
  Evidence: `tests/` currently contains email-channel tests, tool validation tests, and a Docker smoke script.

- Observation: No Teams channel or Bot Framework adapter currently exists in this fork.
  Evidence: code search found no Teams implementation under `nanobot/channels/` or bridge modules.

- Observation: Test execution depends on editable package install in a clean environment.
  Evidence: `pytest -q` failed with `ModuleNotFoundError: No module named 'nanobot'` before `pip install -e ".[dev]"`, and passed after install.

- Observation: CLI smoke usage depends on user bootstrap files under `~/.nanobot`.
  Evidence: `nanobot status` reported missing `~/.nanobot/config.json` and workspace on this machine.

- Observation: Current baseline has critical/high risks that are material for enterprise deployment and must be treated as gating work.
  Evidence: `plan/security-risk-register.md` documents unauthenticated inbound access risk, weak filesystem boundary checks, SSRF exposure in web fetch, and unauthenticated bridge commands.

- Observation: Security baseline hardening reduced default tool/channel permissiveness and may change behavior for previously open local setups.
  Evidence: channel access now defaults to deny-unlisted and high-risk tools are blocked by default policy.

## Decision Log

- Decision: Use a phased, experiment-first approach before any broad refactor.
  Rationale: The fork requirement plus upstream-sync preference makes irreversible early rewrites risky. Small, verifiable spikes reduce lock-in.
  Date/Author: 2026-02-09 / Codex

- Decision: Prefer a profile-based disablement strategy over hard deletion during feasibility.
  Rationale: Feature flags and profile gates reduce merge conflicts with upstream and keep rollback simple while evidence is gathered.
  Date/Author: 2026-02-09 / Codex

- Decision: Treat connector work (Microsoft/Jira/Confluence/Miro) as interface-first in this phase.
  Rationale: Feasibility should prove architectural fit and safety boundaries before introducing external API complexity and secrets handling.
  Date/Author: 2026-02-09 / Codex

- Decision: Add a dedicated Teams feasibility milestone before general connector expansion.
  Rationale: Teams is a direct user-facing requirement for non-technical staff and should be validated early as an optional channel alongside CLI.
  Date/Author: 2026-02-09 / Codex

- Decision: Lock Milestone 1 target contract to OpenAI provider path only for `enterprise_minimal`.
  Rationale: The requirement is ChatGPT/Codex-only backend; encoding this now avoids ambiguous provider policy in Milestone 2.
  Date/Author: 2026-02-09 / Codex

- Decision: Keep existing provider/channel/tool implementations in place for now and enforce enterprise restrictions with profile policies.
  Rationale: Additive policy gates reduce upstream merge friction compared to immediate module deletion.
  Date/Author: 2026-02-09 / Codex

- Decision: Re-sequence milestones so security baseline remediation happens before minimal enterprise profile and Teams work.
  Rationale: Proceeding with channel and profile expansion while known critical/high risks exist would increase exposure and rework.
  Date/Author: 2026-02-09 / Codex

- Decision: Apply default-safe controls globally now (not only after enterprise profile toggle), with config escape hatches for explicit opt-in.
  Rationale: This closes high-impact gaps immediately while keeping bounded configuration-based overrides for non-enterprise experimentation.
  Date/Author: 2026-02-09 / Codex

## Outcomes & Retrospective

Milestone 1 outcome (2026-02-09): baseline environment is reproducible in `.venv`, tests pass after editable install, and the enterprise target contract is documented in `plan/enterprise-inventory.md` with explicit keep/disable/remove candidates.

Security precondition outcome (2026-02-09): a dedicated risk register (`plan/security-risk-register.md`) now captures critical/high issues that must be remediated as Milestone 2 gate criteria before expanding channel or connector scope.

Milestone 2 outcome (2026-02-09): security baseline gate implemented and validated. Critical/high findings in `plan/security-risk-register.md` are marked closed with code and test evidence, and policy defaults are documented in `plan/security-policy-matrix.md`.

Remaining outcomes to summarize at later milestones:

1. Whether enterprise adaptation is feasible with acceptable effort.
2. Which components remain close to upstream and which require a maintained divergence.
3. Estimated ongoing cost of upstream sync and risk controls required.

## Context and Orientation

This repository is a Python assistant framework (`nanobot/`) with optional multi-channel integrations and a Node.js WhatsApp bridge (`bridge/`). The command-line entrypoint and runtime wiring live in `nanobot/cli/commands.py`. The agent orchestration loop, tool execution, and context construction are in `nanobot/agent/`. LLM provider selection and routing are in `nanobot/config/schema.py` and `nanobot/providers/`. Channel adapters are in `nanobot/channels/`. Scheduled behavior is handled by `nanobot/cron/` and `nanobot/heartbeat/`.

For enterprise adaptation, the key question is not only "can we remove features," but "can we remove or disable them in a way that still allows regular upstream pulls." In this plan, "upstream compatibility" means this fork can repeatedly merge changes from upstream (`HKUDS/nanobot`) into this repository with predictable, bounded conflicts; it does not imply pushing enterprise-specific fork changes upstream. "Profile" means a named runtime mode that enables a constrained subset of functionality (for example `enterprise_minimal`) without deleting upstream code prematurely.

## Plan of Work

### Milestone 1: Baseline Inventory and Target Contract

Create a precise inventory of what exists today, classify each capability as Keep, Disable-by-default, or Remove-later, and write a target contract for the enterprise profile. The contract must explicitly state allowed providers, allowed channels, allowed tools, and prohibited behaviors.

Expected new artifact: `plan/enterprise-inventory.md` describing the current surface and target profile.

Acceptance: A reviewer can read `plan/enterprise-inventory.md` and answer "what will still be possible" and "what will be impossible by default" without reading source code.

### Milestone 2: Security Baseline Gate (Pre-Adaptation Hardening)

Close or explicitly contain the critical/high risks identified in `plan/security-risk-register.md` before broader enterprise adaptation proceeds. This includes identity and authorization defaults, tool access controls, filesystem boundary correctness, SSRF controls, and bridge authentication posture.

Expected new artifacts: `plan/security-risk-register.md` (updated with status), `plan/security-policy-matrix.md` (policy defaults and exceptions).

Acceptance: no critical/high item in the risk register remains unaddressed for enterprise profile startup; blocked behaviors fail with explicit policy/security errors and tests cover each closed item.

### Milestone 3: Minimal Runtime Profile Spike

Implement a non-destructive profile gate that boots a minimal assistant with CLI as the baseline interaction and OpenAI/Codex-only provider path. Do not delete upstream provider/channel code in this milestone; wire runtime selection so enterprise mode refuses non-approved providers and only allows explicitly approved channels (initially none by default, with Teams as an optional enablement target).

Expected code touch points are likely in `nanobot/config/schema.py`, `nanobot/cli/commands.py`, and provider/channel initialization code paths.

Acceptance: Running the assistant in enterprise profile works for direct CLI messages, Teams can be enabled explicitly when available, and unsupported provider/channel configurations are rejected visibly.

### Milestone 4: Microsoft Teams Channel Feasibility Spike

Design and implement an additive Teams adapter spike without removing existing channel architecture. The goal is to prove end-to-end routing shape for inbound and outbound chat messages and to choose a production integration path. Evaluate two options and document why one is selected:

1. Bot Framework-style HTTP webhook adapter for Teams messages.
2. Microsoft Graph polling/sync adapter for chat messages.

This milestone can use local stubs and simulated payloads for core feasibility. If credentials and tenant setup are available, optionally run a live Teams proof in a dev tenant.

Expected outcome: an initial `teams` channel module (or prototype module in an enterprise namespace), test fixtures for inbound/outbound mapping, and a short decision report naming the preferred production path.

Acceptance: from a simulated Teams inbound payload, the bus receives an `InboundMessage`, the agent produces a response, and the Teams adapter formats an outbound reply payload correctly.

### Milestone 5: Extension Interface Spike (No External API Dependency Yet)

Define adapter interfaces and stub implementations for future integrations: Microsoft 365/SharePoint, Jira, Confluence, and Miro. Stubs should be testable without network calls and without credentials. The purpose is to prove architecture shape and call flows, not to complete real integrations.

Expected outcome: a new module namespace for enterprise connectors and tests that prove the agent can invoke connector abstractions safely.

Acceptance: A simple local test can call a stub connector through a registered tool and return deterministic output.

### Milestone 6: Upstream Sync Rehearsal

Rehearse merge mechanics by adding upstream remote, creating a sync branch, and performing at least one merge/rebase simulation against current upstream state. Measure conflict count and conflict locations. Use this evidence to finalize the long-term fork strategy.

Acceptance: A short report captures merge conflict hotspots and a recommended branch strategy with update cadence.

## Concrete Steps

All commands below run from repository root:

    cd <repo-root>

1. Baseline environment and tests:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"
    pytest -q

Expected: tests run without import errors. If failures occur, capture exact failures in `Surprises & Discoveries` and continue with scoped fixes.

Executed evidence (2026-02-09):

    pytest -q
    # failed before install with ModuleNotFoundError: No module named 'nanobot'

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"
    pytest -q
    # 13 passed, 1 warning in 2.87s

    nanobot --help
    nanobot status
    # config/workspace missing under ~/.nanobot on this machine

2. Inventory current feature surface:

    rg --files nanobot/channels nanobot/providers nanobot/agent/tools
    rg -n "enabled|restrict_to_workspace|consent_granted|provider|channel" nanobot/config nanobot/cli

Expected: a complete map of integration and safety toggles for the Keep/Disable/Remove matrix.

Executed evidence (2026-02-09):

    rg --files nanobot/channels nanobot/providers nanobot/agent/tools nanobot/config nanobot/cli
    rg -n "enabled|disable|restrict_to_workspace|consent_granted|provider|channel|tool|profile|policy" nanobot/config nanobot/cli nanobot/agent nanobot/channels nanobot/providers

3. Add enterprise profile contract document:

    mkdir -p plan
    # create plan/enterprise-inventory.md with Keep/Disable/Remove and rationale

Expected: concrete contract committed as text before code-level pruning.

Executed evidence (2026-02-09):

    # created plan/enterprise-inventory.md with Keep/Disable-by-default/Remove-later contract

4. Record and prioritize security findings:

    # create and maintain security risk register
    # artifact: plan/security-risk-register.md

Expected behavior example:

    - Each risk has severity, concrete evidence, and mitigation owner/milestone.
    - Critical/high risks are marked as Milestone 2 gate items.

5. Implement security baseline gate and verify:

    # run targeted tests to prove security controls (exact test names to be added in milestone)
    pytest -q -k security

Expected behavior example:

    - Unknown sender on enabled channel is rejected by default.
    - Filesystem tools cannot escape workspace via prefix/symlink tricks.
    - `web_fetch` rejects loopback/private/link-local targets.
    - Unauthenticated bridge commands are rejected.
    - Sensitive config file permissions are enforced.

Executed evidence (2026-02-09):

    # security controls implemented in:
    # nanobot/channels/base.py
    # nanobot/config/schema.py
    # nanobot/security/policy.py
    # nanobot/agent/loop.py
    # nanobot/agent/subagent.py
    # nanobot/agent/tools/filesystem.py
    # nanobot/agent/tools/web.py
    # nanobot/channels/whatsapp.py
    # bridge/src/index.ts
    # bridge/src/server.ts
    # nanobot/config/loader.py
    # nanobot/session/manager.py
    # nanobot/cli/commands.py

    pytest -q
    # 20 passed, 1 warning in 1.37s

6. Implement minimal runtime profile spike and verify:

    # run CLI direct mode with enterprise profile enabled (exact flag/env to be defined in milestone)
    nanobot agent -m "hello"

Expected behavior example:

    - Assistant returns a normal text response in CLI mode.
    - Startup rejects unsupported channel/provider config with explicit error text.

7. Implement Teams channel feasibility spike and verify:

    # run Teams adapter unit tests (exact test file names to be defined in milestone)
    pytest -q -k teams

Expected behavior example:

    - A Teams inbound activity payload is mapped to `InboundMessage(channel="teams", ...)`.
    - An `OutboundMessage(channel="teams", ...)` is mapped to a valid Teams reply payload.

8. Upstream sync rehearsal:

    git remote add upstream https://github.com/HKUDS/nanobot.git
    git fetch upstream --tags
    git checkout -b spike/upstream-sync-rehearsal
    git merge --no-ff upstream/main

Expected: merge succeeds or produces conflicts. Record conflict files and classify whether they are avoidable by architectural isolation.

## Validation and Acceptance

Feasibility is accepted only if all conditions are met:

1. A minimal enterprise profile can run end-to-end in CLI mode using approved provider path, with optional Teams channel enablement.
2. Critical/high security risks from `plan/security-risk-register.md` are closed or explicitly accepted with documented compensating controls.
3. Disallowed capabilities are rejected by policy, with clear user-facing error messages.
4. Teams channel feasibility is proven through local tests and optionally validated in a dev tenant.
5. Extension adapter contracts exist with deterministic local tests and no external credentials.
6. Upstream merge rehearsal demonstrates conflict scope that is operationally manageable.
7. A written recommendation includes effort, risks, and a go/no-go decision with rationale.

Human-verifiable evidence must include command outputs, policy-block examples, and a merge-conflict summary.

## Idempotence and Recovery

This plan is designed to be rerun safely. Profile gating and adapter introduction should be additive, not destructive, during feasibility. If a spike causes instability, disable the enterprise profile flag and confirm default behavior still works. Keep experiments on feature branches and avoid direct edits on `main`.

For risky merge rehearsals, create throwaway branches (`spike/*`) and reset by deleting the branch rather than rewriting shared history. Preserve logs and notes in `plan/` so failed experiments still contribute evidence.

## Artifacts and Notes

Required artifacts to produce during execution:

1. `plan/enterprise-inventory.md` with Keep/Disable/Remove matrix and rationale.
2. `plan/security-risk-register.md` with severity-ranked findings and closure status.
3. `plan/security-policy-matrix.md` with per-profile tool policy.
4. `plan/teams-feasibility-report.md` with chosen integration pattern and tradeoffs.
5. `plan/upstream-sync-report.md` with conflict analysis and recommended maintenance workflow.
6. Updated `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` sections in this file.

Short evidence snippets should be embedded as indented plain text excerpts, for example import errors, policy enforcement messages, and merge conflict summaries.

## Interfaces and Dependencies

During feasibility, define stable interfaces first and keep external dependencies optional:

1. Provider policy interface (new module, additive):

       class ProviderPolicy:
           def is_allowed(self, provider_name: str, model: str) -> bool: ...
           def rejection_reason(self, provider_name: str, model: str) -> str: ...

2. Tool policy interface (new module, additive):

       class ToolPolicy:
           def is_allowed(self, tool_name: str, context: dict[str, str]) -> bool: ...
           def rejection_reason(self, tool_name: str) -> str: ...

3. Connector adapter base interfaces (stubs only in this phase):

       class EnterpriseConnector:
           name: str
           async def health(self) -> dict[str, str]: ...
           async def execute(self, action: str, payload: dict) -> dict: ...

       class MicrosoftConnector(EnterpriseConnector): ...
       class JiraConnector(EnterpriseConnector): ...
       class ConfluenceConnector(EnterpriseConnector): ...
       class MiroConnector(EnterpriseConnector): ...

4. Teams channel adapter interface (for channel-level chat, separate from business connectors):

       class TeamsTransport:
           async def parse_inbound(self, payload: dict) -> dict: ...
           async def build_outbound(self, text: str, context: dict) -> dict: ...

       class TeamsChannel(BaseChannel):
           name = "teams"
           async def start(self) -> None: ...
           async def stop(self) -> None: ...
           async def send(self, msg: OutboundMessage) -> None: ...

Keep these interfaces in a dedicated enterprise namespace so upstream core files need minimal edits. Minimize changes to existing core orchestration unless an experiment proves it is unavoidable.

---

Plan revision note (2026-02-09): Initial ExecPlan created to drive feasibility research and experimentation for enterprise adaptation while preserving upstream sync options.
Plan revision note (2026-02-09): Added explicit Microsoft Teams feasibility milestone and acceptance criteria for Teams chat evaluation.
Plan revision note (2026-02-09): Adjusted Teams scope to be additive with CLI so both interaction paths remain available.
Plan revision note (2026-02-09): Resumed execution; added baseline setup/test evidence, completed Milestone 1 inventory artifact, and updated living sections to reflect observed results and decisions.
Plan revision note (2026-02-09): Added security risk register and re-sequenced milestones so security baseline remediation is an explicit gate before profile/channel expansion.
Plan revision note (2026-02-09): Completed Milestone 2 security baseline implementation with tests, added policy matrix, and updated risk register to closed status for initial critical/high findings.
