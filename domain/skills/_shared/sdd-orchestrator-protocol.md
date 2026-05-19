# SDD Orchestrator Protocol

> Loaded on demand by the orchestrator when SDD is triggered.
> Decision criteria (size classification, delegation, user overrides) live in the adapter's CLAUDE.md.

## Commands

- `/ai-team new <change-name>` -- Start a new SDD change
- `/ai-team ff <change-name>` -- Fast-forward planning: propose → spec → design → tasks (apply/verify/archive remain manual)
- `/ai-team continue [change-name]` -- Resume an active change
- `/ai-team status [change-name]` -- Show change progress
- `/ai-team explore <topic>` -- Investigate a codebase topic without starting SDD
- `/ai-team baseline <domain>` -- Document current state of an existing domain

## Auto-Init (before any SDD phase)

Before executing any SDD command (`/ai-team new`, `/ai-team ff`, `/ai-team continue`, `/ai-team explore`, `/ai-team baseline`):

1. Check if `.ai-team/config.yaml` exists in the project root
2. If it exists: proceed normally
3. If missing:
   a. Create `.ai-team/` directory structure inline (dirs + .gitignore)
   b. Delegate to sdd-scout in bootstrap mode to detect the stack
   c. Wait for the scout to finish and verify `config.yaml` was created
   d. Then proceed with the originally requested command

Do NOT ask the user to run init — handle it transparently.

### Directory structure (create inline)

```
.ai-team/
  specs/
  changes/archive/
  explorations/
  .gitignore
```

The `.gitignore` should ignore active changes and explorations but keep specs and archive:

```
/changes/*
!/changes/archive/
/explorations/
```

## Dependency Graph

Standard path (`change_type: feature` or `mixed`):

```
proposal --> [security:tm if sensitive] --> specs ---> tasks --> apply --> [orchestrator-audit] --> [security:ca if sensitive] --> verify --> archive
                                         -> design -/
```

Infra-only short path (`change_type: infra`, user approved skip-spec):

```
proposal --> [security:tm if sensitive] --> design --> tasks --> apply --> [orchestrator-audit] --> [security:ca if sensitive] --> verify --> archive
```

Convention: bracketed phases are conditional. Readers infer the condition from the Approval Gates table (the `Conditional on` column).

| Phase | Skill | Requires (standard) | Requires (infra short path) | Produces |
|-------|-------|---------------------|------------------------------|----------|
| propose | sdd-propose | -- | -- | `proposal.md` |
| spec | sdd-spec | proposal | (skipped) | `specs/{domain}/spec.md` |
| design | sdd-design | proposal | proposal | `design.md` |
| tasks | sdd-tasks | specs, design | design | `tasks.md` |
| apply | sdd-apply | tasks | tasks | code changes |
| verify | sdd-verify | tasks | tasks | verification report |
| archive | sdd-archive | verify | verify | merged specs (no-op if no specs) |
| security-threat-model | sdd-security (mode: threat-model) | proposal-approval | proposal-approval | `threat-model.md` |
| security-code-audit   | sdd-security (mode: code-audit)   | apply            | apply            | `audit-report.md` |

Utility: **sdd-scout** (bootstrap, explore, baseline) -- invoked by the orchestrator, not part of the DAG.

Before starting any phase:

1. Check the Requires column -- verify all required artifacts exist
2. If any are missing, run the previous phase first
3. If all present, delegate to the phase's skill

## Automatic Baseline Detection

Before the **spec phase**, check if a base spec exists for each domain affected by the change:

1. Read the proposal to identify affected domains
2. For each domain, check if `.ai-team/specs/{domain}/spec.md` exists
3. If missing: inform user, delegate to sdd-scout in baseline mode, wait, then proceed
4. If all exist: proceed normally

## Fast-Forward Workflow

`/ai-team ff <change-name>` chains the planning phases (propose → spec → design → tasks) into a single invocation. Apply, verify, and archive still require explicit `/ai-team continue`.

**Sequence:** Auto-Init → propose → proposal-approval gate → spec (skipped if infra short-path) → security threat-model gate (if `security_touchpoints` non-empty) → design → tasks → Stop (report summary; do NOT continue into apply).

**Mode:** ask once per session: `auto` (back-to-back, pause only at gates) or `interactive` (default — pause after each phase, show summary, ask "Continue?"). On any `needs_input` or failure: FF aborts; report which phase stopped and what to do next.

**Sub-agent contract:** `execution_mode` is an orchestrator concern only. Sub-agents do NOT receive this flag; they run end-to-end and return their envelope regardless of mode.

## Approval Gates

| Gate | After | Before | Conditional on |
|------|-------|--------|----------------|
| **Proposal approval** | propose | spec, design | always |
| **Security: threat-model** | proposal-approval | spec, design | `security_touchpoints` non-empty |
| **Apply approval** | tasks | apply | always |
| **Security: code-audit** | apply | verify | `security_touchpoints` non-empty |

At each gate:
1. Present a concise summary of the completed phase
2. Ask the user: approve, request changes, or cancel
3. Do NOT proceed until explicitly approved

### Proposal approval — infra-only short path

When `sdd-propose` returns `change_type: "infra"` in its envelope (and the proposal.md `Change Type` section confirms it), present the user a third option in the approval gate:

> Proposal classified as **infra-only** (no new business requirements). You can skip the spec phase and go straight to design + tasks. Spec adds ~30-50k tokens of overhead and provides little value when there are no business rules to document.
>
> Options:
> - **Approve + skip spec** (faster, recommended for pure infra)
> - **Approve + run spec** (default, conservative)
> - **Request changes** / **Cancel**

**Default if user is ambiguous**: run spec. Only skip when the user explicitly says "skip spec" / "salta spec" / "infra path" / picks the option by name.

When the user picks skip-spec:
- Mark `phases.spec.status: "skipped"` in `state.yaml` with `skip_reason: "infra-only change, user approved"`
- Skip baseline detection for spec (specs/{domain}/spec.md is not required)
- Delegate `sdd-design` only; tasks phase reads design without spec
- Verify and archive proceed normally; verify's traceability matrix maps ACs from proposal directly to tests (no requirement IDs)

When `change_type` is `feature` or `mixed`, do NOT offer the skip option — run spec normally.

### Security gates

**When to enter the gate:** Read `security_touchpoints` from the most recent `sdd-propose` envelope. If non-empty, run the security gate; if `[]`, skip silently.

#### threat-model gate flow

1. Delegate `sdd-security` with `mode: threat-model`, model `opus`, injected `security_touchpoints` and `proposal_path`.
2. Inspect returned envelope. If `verdict: critical`: present override prompt (3 options — see below).
3. If `verdict: no-findings` or `warnings-only`: no override prompt — pass straight to spec/design.
4. Inject the envelope's `security_requirements` into the next phase delegation prompt (spec phase normally; design phase if `skip_spec: true` per Q6).

#### code-audit gate flow

1. Delegate `sdd-security` with `mode: code-audit`, model `sonnet`, injected `tasks_path`, `change_branch`, `base_branch`. Note: `base_branch` MUST be the merge-base of the change branch (not `main`) — see DR-10.
2. Inspect returned envelope. If `verdict: critical`: present override prompt.
3. If `verdict: no-findings` or `warnings-only`: no override — pass to verify.

#### Override prompt (3 options) — exact wording

> Security gate produced **{N} CRITICAL finding(s)**:
>
> {one-line summary per CRITICAL finding from the artifact}
>
> Options:
> - **Fix and re-run** — close this run; you address the findings and the orchestrator re-runs the gate.
> - **Accept and proceed** — log the override in `state.yaml.decisions:` and continue. You will be asked for the override `reason` (one sentence) and the override `evidence` field will reference the finding ID(s).
> - **Cancel the change** — abort. The change directory remains for inspection.

#### Cancel write rule (REQ-ORCHESTRATOR-003 Scenario O3.3)

When the user picks "Cancel the change":
1. Write `state.yaml.blocked: true`.
2. Write `state.yaml.blocked_reason: "Security gate: user cancelled on finding(s) {finding-id-list}"`.
3. Stop. Do NOT delete the change directory. Do NOT continue to spec/verify.

#### Override write rule (accept-and-proceed)

Write a `decisions:` entry:

```yaml
- date: {now}
  phase: security-threat-model    # or security-code-audit
  task_ref: "security-override"
  decision: "Accept CRITICAL security finding(s) {finding-id-list}"
  reason: "{user-provided one sentence}"
  evidence: "{artifact-path}#finding-{id}"
  commits: []
```

#### Q7 — Override-propagation rule

When an override happens during threat-model, append to the spec delegation prompt under:

```
## Overridden Security Findings (informational SHOULD)
The following findings were ACKed by the user but should be captured as informational SHOULD requirements per `decisions:` entry {N}:
- {finding-id}: {finding text}
```

The spec phase ingests these as SHOULD requirements with a footnote linking to the override. Verify treats them as informational.

#### Q6 — Infra short path interaction

When `change_type: infra` AND `security_touchpoints` non-empty:
- Still run the threat-model gate.
- Route `security_requirements` into the design phase delegation prompt (not spec, which is skipped).
- Design incorporates them as constraint sections; tasks reads them from design.md.

## Re-engage Routing on failure_class

When sdd-verify returns a non-null `failure_class`, route as follows:

| `failure_class` | Re-engage target | Action |
|-----------------|-----------------|--------|
| `implementation` | `sdd-apply` | Code is wrong; test contract is correct; apply fixes the code |
| `test_contract` | `sdd-tasks` | Test is wrong; tasks re-evaluates the scaffold and AC↔test mapping |
| `spec_gap` | User (escalate) | Spec ambiguous or AC decomposition incomplete; clarify before re-engaging |

**Max retries:** 3 per logical group. After 3 failed verify attempts on the same group (any failure_class), escalate to user presenting full failure history. Counter resets if the group's verdict changes to PASS.

A "re-engage attempt" = each delegation of sdd-apply or sdd-tasks for the same group after verify FAIL.

### Apply-Blocked Re-engage Routing on `deviation_report.kind`

Two trigger sources feed re-engage: verify's `failure_class` (post-verify) and apply's
`deviation_report.kind` (apply-blocked, before verify).

| `deviation_report.kind` | Re-engage target | Action |
|--------------------------|------------------|--------|
| `out-of-plan` | `sdd-apply` (refined scope) OR user (escalate) | Orchestrator inspects evidence; if drift is mechanical and scoped, approve, write `decisions[]` (`task_ref: "out-of-plan"`), re-engage apply with the approved drift inlined. If scope creep is ambiguous, escalate to user with the evidence block. |
| `design-pivot` | `sdd-design` | Re-engage design with the failed assumption inlined (file:line from `deviation_report.evidence`). Design re-emits `design.md`; downstream tasks/apply rerun. Write `decisions[]` (`task_ref: "design-pivot"`) capturing the orchestrator's pivot decision. |
| `test-orphan` | `sdd-tasks` | Re-engage tasks with the failed test name + missing-entity grep result inlined (extracted from `deviation_report.evidence`). Tasks re-emits the scaffold OR expands scope to add the entity (justified by a REQ). Write `decisions[]` (`task_ref: "test-orphan-re-engage"`) capturing the orchestrator's route decision. |

**Re-engage prompt template for test-orphan** — when orchestrator re-engages sdd-tasks on
`deviation_report.kind: test-orphan`, the delegation prompt MUST include a block:

```
## Re-engage Reason
Apply blocked on a test-orphan (REQ-APPLY-023). The test scaffold references an entity
that does not exist in the system under test.

- Failed test: {deviation_report.evidence.file}:{line or test name}
- Missing entity: {extracted from deviation_report.evidence.output}
- Grep result: {deviation_report.evidence.output}

Re-evaluate the test contract:
(a) If the test is wrong → correct the scaffold (rewrite tasks.md scaffold section,
    update AC↔Test Traceability).
(b) If the entity should exist (justified by a REQ) → expand scope; add a new task for
    the entity (with REQ trace).
(c) If neither (spec ambiguous) → return status: needs_input.
```

**Max retries:** unchanged (3 per logical group). A test-orphan re-engage counts as one
attempt for the group.

## work-unit-commits Invocation

After sdd-verify returns GREEN (PASS or PASS WITH WARNINGS) for a logical group, invoke work-unit-commits:

```
Inject: group_id={G_id}, mode={config.commit_strategy default auto if absent}, change_name={change_name}
```

- Invoke ONLY after verify GREEN; never after FAIL.
- Read `commit_strategy` from `.ai-team/config.yaml`; default `auto` if field absent.
- `tasks_in_group` is derived by work-unit-commits from tasks.md; do NOT inject it.
- Model: sonnet.

## Deviation Report Ingestion

When apply returns `status: blocked` with `deviation_report` populated, the orchestrator MUST:

1. Read `deviation_report.kind`, `task_ref`, `evidence`, `suggested_action`.
2. Author one `decisions[]` entry in `state.yaml`:
   ```yaml
   - date: {current_iso_utc}
     phase: orchestrator
     task_ref: {map kind → task_ref value below}
     decision: "Orchestrator handled apply-blocked: {one-sentence summary}"
     reason: "{from suggested_action context, one sentence}"
     evidence: "{deviation_report.evidence.file}:{line} — {deviation_report.evidence.command}\n{deviation_report.evidence.output truncated to 200 chars}"
     commits: []
   ```
3. Map `deviation_report.kind` to `task_ref`:
   - `out-of-plan` → `task_ref: "out-of-plan"`
   - `design-pivot` → `task_ref: "design-pivot"`
   - `test-orphan` → `task_ref: "test-orphan-re-engage"`
4. Take the action per `deviation_report.suggested_action` (orchestrator may override based
   on its full-pipeline view):
   - `re-engage-tasks` → delegate sdd-tasks with re-engage prompt template (see above)
   - `re-engage-design` → delegate sdd-design with the failed assumption inlined
   - `re-engage-apply-refined` → delegate sdd-apply with the approved drift inlined as
     additional scope
   - `escalate-user` → present `deviation_report.evidence` to user; user picks action
5. Update `state.yaml.updated: {current_iso_utc}`.

## Post-Apply Independent Audit (Thin Red-Network)

After sdd-apply completes, run the four structural greps from REQ-VERIFY-004:
- Check 1: `git diff --name-only HEAD` vs tasks.md Files: blocks (undeclared files → WARNING)
- Check 2: grep decisions[].decision tokens against diff (zero hits → WARNING)
- Check 3: count decisions[] apply entries vs fix: commits (fix-commits > entries → WARNING)
- Check 4: count new test files vs test count delta in the baseline (discrepancy → WARNING)
- **Check 5 — Compilability sanity (BLOCKING):** Read `config.yaml` verify commands (typecheck, lint, test) and run them, scoping the test invocation to files in `git diff --name-only HEAD` from the apply session. Capture exit codes. **Blocking semantics:** any verify command with `exit_code != 0`, OR any entry in apply's reported `execution_evidence.tests_created[]` with `exit_code != 0`, → re-engage `sdd-apply` with the specific failures inlined in the re-engage prompt. Do NOT delegate `sdd-verify` until Check 5 is clean. Log a `decisions[]` entry with `task_ref: post-apply-audit-gap` listing what failed. If `execution_evidence` is absent or empty in the apply envelope → treat as Check 5 failure and re-engage apply.

On agreement with sdd-apply's envelope (Checks 1-4): delegate sdd-verify normally.
On any Check 1-4 discrepancy: present WARNING to user ("Pre-verify audit found: {finding}. sdd-verify will rule authoritatively."). Then delegate sdd-verify regardless — it provides the authoritative ruling.
On Check 5 failure: re-engage sdd-apply (blocking). Do NOT delegate sdd-verify until Check 5 is clean.

Checks 1-4 do not block verify delegation (informational WARNINGs surfaced to user, sdd-verify runs authoritatively). Check 5 DOES block — re-engage apply until clean before delegating verify.

## Plan Mode (NOT used inside the SDD pipeline)

**Plan mode is NOT entered during the SDD pipeline.** The pipeline's own approval gates are sufficient.

**Orchestrator flow for SDD:**
1. Classification gate triggers Large → user chooses SDD (plan mode may be active at this point)
2. **Exit plan mode** (`ExitPlanMode`) as soon as the user confirms SDD
3. Run auto-init → health check → delegate phases per Dependency Graph → no plan mode at any point

**When the orchestrator might still edit code:** the user explicitly requests an inline edit during SDD. The orchestrator can do it without plan mode. The pipeline gates still protect the larger artifacts.

## Health Check (before propose)

Before delegating to `sdd-propose` on `/ai-team new`, establish a test-suite baseline so `sdd-verify` can later distinguish regressions from pre-existing failures.

### When to run

- `/ai-team new <change>` — always, after auto-init, before delegating propose
- `/ai-team continue` — skip (baseline was captured on the original `new`)
- `/ai-team explore`, `/ai-team baseline`, `/ai-team status` — skip (not a change run)

### How to run

1. Read `.ai-team/config.yaml` → look for `test_commands:` section (e.g., `unit:`, `integration:`)
2. If `test_commands` exists, delegate to a sonnet sub-agent:
   - Run each configured command
   - Capture: exit code, pass/fail counts (parse the test runner output), last 20 lines of stderr
   - Capture: `git rev-parse HEAD` for the commit reference
   - Write `.ai-team/changes/{change-name}/baseline.md`
3. If `test_commands` is missing: skip the health check, note it as a risk in the proposal delegation prompt, and proceed. Do NOT block on missing config — this is a best-effort safety net, not a hard requirement.

**Baseline file format:** `# Baseline — {change-name}` → `**Date/Git HEAD/Branch**` → `## Test Runs` with one subsection per command (command + exit code + summary + top failures if any). Include a `## Notes` section for pre-existing failures. sdd-verify reads this to exclude pre-existing failures from regression counts.

### How verify uses the baseline

`sdd-verify` MUST read `.ai-team/changes/{change}/baseline.md` (if present) before reporting test failures. Any failure that exists in the baseline is NOT a regression — it's pre-existing and out of scope for this change. Verify reports only deltas.

## State Recovery

After context compaction or session restart:

1. Check for `.ai-team/changes/` directory
2. Read `state.yaml` for each active change
3. Reconstruct where things stand from the `current_phase` field
4. Resume from the current phase

This is why `state.yaml` is the source of truth -- it survives context loss.

## Model Routing

Model routing only applies to **delegated sub-agents**. Inline work runs at whatever model the user has selected for the session.

Read this table at session start, cache it, and pass the model in every `Agent()` call. If a phase is missing, use `sonnet`. If the assigned model is unavailable, fall back to `sonnet`.

| Phase | Model | Reason |
|-------|-------|--------|
| sdd-scout | sonnet | Codebase exploration, structured output |
| sdd-propose | opus | Architectural analysis, scope decisions |
| sdd-spec | sonnet | Structured writing from clear input |
| sdd-design | opus | Interface decisions, data flow architecture |
| sdd-tasks | sonnet | Mechanical breakdown from clear design |
| sdd-apply | sonnet | Code generation from specs |
| sdd-verify | sonnet | Validation against spec |
| sdd-archive | sonnet | Memory capture + destructive Bash (cp/rm); haiku auto-restricts on cleanup, see [[haiku-bash-auto-restrict]] |
| sdd-security (threat-model) | opus   | Architectural reasoning across the proposal surface |
| sdd-security (code-audit)   | sonnet | Pattern matching over the diff |
| work-unit-commits | sonnet | — |
| default | sonnet | Non-SDD general delegation |

### Project Override

Check `.ai-team/config.yaml` for `model_overrides` -- project-level overrides take priority over the defaults above.

## Sub-Agent Delegation

IMPORTANT: Always use `subagent_type: "general-purpose"`. Do NOT invent custom subagent types like "sdd-propose" — they don't exist and will error.

**Delegation pattern (applies to every SDD phase):**
1. Read `skills/sdd-{phase}/SKILL.md` yourself (the orchestrator reads it; sub-agents do NOT search for skill files).
2. Read the shared protocols yourself.
3. Inject both as text into the `Agent()` prompt. Sub-agents receive instructions inline.
4. Inject `references_dir: skills/sdd-{phase}/references/` — the sub-agent reads reference files on demand; the orchestrator does NOT paste them inline.
5. If `strict_tdd: true` and the phase is `apply` or `verify`, append: "STRICT TDD MODE IS ACTIVE. Test runner: `{config.yaml → test_commands.unit}`. Follow red → green → triangulate → refactor."

**Prompt structure:** `You are the sdd-{phase} executor. Do this phase's work yourself. Do NOT delegate.` → `## Injected Context` (per Critical Context Forwarding table) → `## Instructions` (SKILL.md contents) → `## Shared Protocols` (context-protocol, persistence-contract, result-envelope, spec-convention, evidence-protocol) → `## Task` (what to do) → `## Project Root` (absolute path) → `## Expected Output` (result envelope with `model_used` and `context_resolution`).

### Critical Context Forwarding

Sub-agents are born with **no memory** of prior phases. The orchestrator is the only component that holds session state, so it MUST inject every piece of context the next phase needs — directly into the delegation prompt. Do NOT rely on the sub-agent to discover flags by grepping or by reading state files; discovery is flakey and silently degrades.

Resolve these flags **once per session**, cache them, and inject them into every relevant delegation:

| Flag | Resolved from | Inject in (phases) | When mandatory |
|------|---------------|--------------------|----------------|
| `change_name` | user command | every phase | always |
| `change_dir` | `.ai-team/changes/{change_name}` | every phase | always |
| `model_alias` | Model Routing table | every phase | always |
| `change_type` | `sdd-propose` envelope (`infra` / `feature` / `mixed`) | design, tasks, apply, verify, archive | once propose has run |
| `skip_spec` | proposal approval gate (true if user picked skip-spec on infra) | design, tasks, apply, verify, archive | once gate has resolved |
| `baseline_path` | `.ai-team/changes/{change_name}/baseline.md` | apply, verify | if file exists |
| `proposal_path` | `.ai-team/changes/{change_name}/proposal.md` | spec, design, tasks, verify | once propose has run |
| `design_path` | `.ai-team/changes/{change_name}/design.md` | tasks, apply, verify | once design has run |
| `spec_paths` | `.ai-team/changes/{change_name}/specs/*/spec.md` (list) | tasks, apply, verify, archive | once spec has run; pass empty list on infra short path |
| `tasks_path` | `.ai-team/changes/{change_name}/tasks.md` | apply, verify | once tasks has run |
| `strict_tdd` | `.ai-team/config.yaml` → `strict_tdd: true` (if present) | apply, verify | if config sets it |
| `security_touchpoints` | `sdd-propose` envelope (list of touchpoint slugs; empty list = not sensitive) | every phase after propose | once propose has run |
| `references_dir` | `skills/sdd-{phase}/references/` (literal — not project-relative) | every phase | always |
| `current_iso_utc` | `date -u +%Y-%m-%dT%H:%M:%SZ` (orchestrator at delegation time) | every phase that writes `state.yaml` | always |
| `group_id` | tasks.md (the just-passed group) | work-unit-commits | always when invoking work-unit-commits |
| `mode` | `.ai-team/config.yaml.commit_strategy` (default auto) | work-unit-commits | always when invoking work-unit-commits |

Inject all fields from the table above as a `## Injected Context (from orchestrator)` block at the top of the delegation prompt. The sub-agent treats this block as the source of truth for paths and flags — it does NOT re-derive them from disk.

When `strict_tdd: true`, append to apply/verify prompts: "STRICT TDD MODE IS ACTIVE. Test runner: `{config.yaml → test_commands.unit}`. Follow red → green → triangulate → refactor."

### Context Resolution Feedback

Every result envelope includes `context_resolution: injected | fallback | none`. On `fallback`: re-read `state.yaml` and prior phase envelopes, rebuild the flag cache from the Critical Context Forwarding table, and inject the rebuilt block in all subsequent delegations. Surface one warning: `"Detected cache miss in {phase} — reloaded session state."` Never ignore `fallback` — silent degradation is exactly what this loop prevents.

### Non-SDD Delegation

For medium tasks that benefit from delegation but don't warrant full SDD: use `model: sonnet`, include relevant project context (config.yaml, applicable skills), give clear file-path instructions, and request a brief summary (not a full envelope).

### Delegating to sdd-security

Use the standard delegation pattern (see above) with the following sdd-security-specific Injected Context fields:

**threat-model** (after proposal approval, before spec/design — model: opus):
```
mode: threat-model
proposal_path: .ai-team/changes/{name}/proposal.md
security_touchpoints: [{slug}, ...]
```

**code-audit** (after apply, before verify — model: sonnet):
```
mode: code-audit
tasks_path: .ai-team/changes/{name}/tasks.md
change_branch: {branch}
base_branch: {merge-base-sha}   # MUST be git merge-base main {branch}, NOT "main" (DR-10)
```

## Tool Availability by Phase

Sub-agents inherit Bash from the parent session — they CAN run commands. The harness does not message the model when Bash would be denied; auto-restriction is a model behavior, not a permission gate. Each phase prompt MUST make availability explicit.

The orchestrator forwards the relevant block below as Injected Context when delegating to each phase. Sub-agents reading this contract MUST NOT return `needs_input` on the assumption that Bash is unavailable — they MUST attempt the command first and only escalate on real failure (non-zero exit captured in output).

### apply
- Bash: AVAILABLE. Run the verify commands declared in `config.yaml` (typecheck, lint, test, build) and the read-only git commands `git status` and `git diff --name-only` freely. NEVER invoke `git commit`, `git add`, `git push`, `git stash`, `git reset`, or `git rm` — work-unit-commits owns commits (REQ-APPLY-021).
- Destructive: not expected at this phase. If a task requires `rm -rf` or `cp -r` outside the working tree, return `needs_input` listing the exact command and reason.

### verify
- Bash: AVAILABLE. Step 5 (test execution) is mandatory and non-skippable.
- Writes: read-only on application code. Only `verification-report.md` + `state.yaml` may change.
- Honesty: a spec scenario is COMPLIANT only when a test that covers it has PASSED with captured output. If unable to execute the suite, return `status: needs_input` listing the required commands — never declare COMPLIANT on inference.

### archive
- Bash: AVAILABLE. Run `cp -r .ai-team/changes/{name}/ .ai-team/changes/archive/` and `rm -rf .ai-team/changes/{name}/` per Steps freely.
- Safety net: the `memory_candidates`-first Hard Rule still applies — if any destructive step fails despite Bash being available (collision, permission edge case, disk error), return `status: warning` with the populated `memory_candidates` intact.

## Archive Memory-Capture Handoff

When `sdd-archive` returns its envelope, inspect the `memory_candidates:` field. The sub-agent surfaces tribal knowledge that would otherwise be lost when the change directory is deleted, but it has no access to the orchestrator's memory system — it is your job to grade and persist them.

For each candidate:

1. Read the `type`, `title`, `body`, `rationale`, and `surface` fields.
2. Decide:
   - **Save** — non-obvious, not derivable from current code, will help future sessions. Write the memory file (per memory protocol) and add a pointer to `MEMORY.md`.
   - **Skip** — already in code/CLAUDE.md, generic, or duplicates an existing memory. Note the reason briefly when you summarize to the user.
   - **Merge** — extend an existing memory file rather than creating a new one when the topic overlaps.
3. Summarize the result to the user in 2-3 lines: "Archive surfaced {N} candidates: saved {X}, merged {Y}, skipped {Z}."

If `memory_candidates: []` (empty), no action — proceed to wrap up the SDD run.

This handoff is the cheapest place in the pipeline to capture knowledge. Do NOT skip it because the run "felt routine" — the candidates list is precisely the agent's judgment about what was non-routine.

## Error Handling

| Situation | Action |
|-----------|--------|
| Sub-agent returns `failed` | Report error to user, suggest retry |
| Sub-agent returns `blocked` | Show blocker, ask user for resolution |
| Sub-agent returns `needs_input` | Show questions to user, then re-delegate with answers |
| Sub-agent returns `warning` | Show risks, ask if user wants to proceed |
| Missing artifact | Check if previous phase completed; if not, run it first |
| `apply` returns `ok` but `state.yaml.decisions:` is empty AND `git diff` shows files outside `tasks.md` | Apply skipped the mid-flight log. Ask the user whether to retroactively populate decisions before proceeding to verify, or accept the drift as un-logged (verify will flag it). |
| `apply` returns `blocked` with `deviation_report` | Ingest per **Deviation Report Ingestion** subsection above. Author a `decisions[]` entry mapping `deviation_report.kind` → `task_ref`. Take action per `deviation_report.suggested_action`. Do NOT proceed to verify. |
