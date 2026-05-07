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
proposal --> [security:tm if sensitive] --> specs ---> tasks --> apply --> [security:ca if sensitive] --> verify --> archive
                                         -> design -/
```

Infra-only short path (`change_type: infra`, user approved skip-spec):

```
proposal --> [security:tm if sensitive] --> design --> tasks --> apply --> [security:ca if sensitive] --> verify --> archive
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

`/ai-team ff <change-name>` chains the planning phases (propose → spec → design → tasks) into a single invocation. Conceptually equivalent to running `/ai-team new <name>` followed by `/ai-team continue` until tasks completes. Apply, verify and archive are out of scope and still require explicit `/ai-team continue`.

### Sequence

1. Auto-Init (per the section above) if `.ai-team/config.yaml` is missing.
2. Delegate to `sdd-propose`.
3. **Proposal approval gate (blocking)** — same behavior as the standard path. Pause, present the proposal, wait for user approval. Honour the infra short-path (skip-spec) if `change_type: infra`.
4. Delegate to `sdd-spec` (skipped if the user took the infra short-path).
5. **Security threat-model gate (blocking, conditional)** — fires only if the proposal envelope reports `security_touchpoints: [...]` non-empty. Same delegation contract as the standard path.
6. Delegate to `sdd-design`.
7. Delegate to `sdd-tasks`.
8. Stop. Report final summary. Do NOT continue into apply.

### Execution mode

On the first `/ai-team ff` invocation in a session, ask the user which mode to use and cache the answer for the rest of the session (do not ask again unless the user explicitly changes it):

- **`auto`** — runs phases back-to-back. Pauses ONLY at blocking gates (proposal approval, security threat-model). Reports a single combined summary with the four phase outputs at the end.
- **`interactive`** (default) — after each phase completes, show a concise summary of what the phase produced + what the next phase will do, then ask "¿Continuamos?" / "Continue?". Accept yes / no / specific feedback. If feedback is given, incorporate it before launching the next phase.

If the user does not specify, default to `interactive` (safer; gives the user control).

### Behavior at blocking gates

In both modes the orchestrator pauses at every blocking gate:

- **Proposal approval**: pause, present the proposal, wait for OK. On rejection or cancel, FF aborts; report where it stopped.
- **Security threat-model** (only if `security_touchpoints` non-empty): pause, present findings, wait for OK. On cancel, FF aborts and writes `state.yaml.blocked: true` with `blocked_reason` listing the finding IDs (same as the standard path).

### Failure / `needs_input`

If any phase returns `status: needs_input` or fails, FF aborts immediately. Report:
- Which phase stopped the FF.
- The phase's reason (`needs_input` questions or error).
- What the user can do next (`/ai-team continue` once resolved, or restart with adjusted inputs).

### Note on sub-agent contract

`execution_mode` is an orchestrator concern only — it controls whether the orchestrator pauses between phases. Sub-agents do NOT receive this flag; their contract (Critical Context Forwarding) is unchanged. Each phase still runs end-to-end and returns its envelope; the orchestrator decides whether to launch the next phase immediately (auto) or pause for user feedback (interactive).

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

## Plan Mode (NOT used inside the SDD pipeline)

**Plan mode is NOT entered during the SDD pipeline.** The pipeline's own approval gates (proposal approval after propose, apply approval after tasks) are sufficient to prevent unintended changes.

### Why plan mode is off for SDD

- **The pipeline gates already protect against unintended changes**: propose-approval before any spec/design work, apply-approval before any code is written. Adding plan mode on top is redundant.
- **Harness bug**: in the real Claude Code harness, plan mode propagates to delegated sub-agents. A sub-agent launched while the orchestrator is in plan mode cannot write artifacts — it silently stages everything in its own plan file. This was observed in ECO-944 (propose 1st run wasted ~86k tokens on a blocked write).
- **The adapter's classification gate still uses plan mode for Medium and Large-declines-SDD tasks** — it's only inside the SDD pipeline that plan mode is avoided.

### Orchestrator flow for SDD

1. Classification gate triggers Large → user chooses SDD (plan mode may be active at this point from the classification gate — see adapter CLAUDE.md)
2. **Exit plan mode** (`ExitPlanMode`) as soon as the user confirms SDD
3. Run auto-init if needed (creates `.ai-team/` dirs)
4. Run health check (see next section)
5. Delegate propose → approval gate → delegate spec + design in parallel → delegate tasks → approval gate → delegate apply → delegate verify → delegate archive
6. No plan mode at any point in this flow

### When the orchestrator might still edit code during SDD

In practice, almost never. The orchestrator coordinates — it delegates all writes to sub-agents. If the user explicitly asks for an inline edit during SDD (e.g., "just fix this typo real quick"), the orchestrator can do it without plan mode. The pipeline gates still protect the larger artifacts.

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

### Baseline file format

```markdown
# Baseline — {change-name}

**Date:** 2026-04-24T10:30:00Z
**Git HEAD:** {commit-sha}
**Branch:** {branch-name}

## Test Runs

### unit
- **Command:** `{command}`
- **Exit code:** 0
- **Summary:** 3012 passed, 0 failed, 0 skipped
- **Duration:** 12s

### integration
- **Command:** `{command}`
- **Exit code:** 1
- **Summary:** 200 passed, 23 failed (DoctrineSignatureRepository — pre-existing, column `metadata` missing)
- **Duration:** 180s
- **Failures (top 5):**
  - `...::testFoo` — `column metadata does not exist`
  - ...

## Notes

- 23 integration failures pre-exist on this branch (unrelated to this change). Verify phase should treat these as baseline noise.
```

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
| sdd-archive | haiku | Copy and close |
| sdd-security (threat-model) | opus   | Architectural reasoning across the proposal surface |
| sdd-security (code-audit)   | sonnet | Pattern matching over the diff |
| default | sonnet | Non-SDD general delegation |

### Project Override

Check `.ai-team/config.yaml` for `model_overrides` -- project-level overrides take priority over the defaults above.

## Sub-Agent Delegation

IMPORTANT: Always use `subagent_type: "general-purpose"`. Do NOT invent custom subagent types like "sdd-propose" — they don't exist and will error.

When delegating to an SDD phase sub-agent:

1. Read `skills/sdd-{phase}/SKILL.md` yourself
2. Read the shared protocols yourself
3. Inject both as text into the prompt — sub-agents receive instructions inline, they do NOT read skill files

```
Agent({
  description: "sdd-{phase}: {brief task description}",
  subagent_type: "general-purpose",
  model: "{resolved-model}",
  prompt: `
You are the sdd-{phase} executor.
Do this phase's work yourself. Do NOT delegate or launch sub-agents.
Do NOT search for SKILL.md files or skill registries — your instructions are below.

## Injected Context (from orchestrator)
{populate per Critical Context Forwarding table — change_name, change_dir, model_alias, plus phase-specific flags and paths}

## Instructions
{paste contents of skills/sdd-{phase}/SKILL.md here}

## Shared Protocols
{paste contents of skills/_shared/context-protocol.md}
{paste contents of skills/_shared/persistence-contract.md}
{paste contents of skills/_shared/result-envelope.md}
{paste contents of skills/_shared/spec-convention.md}
{paste contents of skills/_shared/evidence-protocol.md}

## Task
{Clear description of what to do — references the paths from Injected Context, does not re-list them}

## Constraints
{Project-specific constraints or user preferences}

## Project Root
{absolute path to target project}

## Expected Output
Return a result envelope per the Result Envelope protocol above.
Include model_used: "{resolved-model}" and context_resolution in the envelope metadata.
`
})
```

If `strict_tdd: true` and the phase is `apply` or `verify`, append the literal "STRICT TDD MODE IS ACTIVE..." instruction (see Critical Context Forwarding) at the end of the prompt.

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

Inject as a labelled block at the top of the delegation prompt:

```
## Injected Context (from orchestrator)
change_name: oauth-login
change_dir: .ai-team/changes/oauth-login
model_alias: sonnet
change_type: feature
skip_spec: false
proposal_path: .ai-team/changes/oauth-login/proposal.md
spec_paths:
  - .ai-team/changes/oauth-login/specs/auth/spec.md
design_path: .ai-team/changes/oauth-login/design.md
tasks_path: .ai-team/changes/oauth-login/tasks.md
baseline_path: .ai-team/changes/oauth-login/baseline.md
strict_tdd: false
security_touchpoints: ["auth/authz", "crypto"]   # or [] for non-sensitive
```

The sub-agent treats this block as the source of truth for paths and flags. It does NOT re-derive them from disk unless explicitly told to.

**Strict TDD example** — when `strict_tdd: true`, also append a literal instruction to apply/verify prompts:

> STRICT TDD MODE IS ACTIVE. Test runner: `{config.yaml → test_commands.unit}`. You MUST follow the strict-tdd module: red → green → triangulate → refactor. Do NOT fall back to standard mode.

This is non-negotiable. Do not rely on the sub-agent to discover the flag by reading config — inject it.

### Context Resolution Feedback

Every result envelope includes `context_resolution: injected | fallback | none`. The orchestrator MUST inspect this field after every delegation:

| Reported value | Orchestrator action |
|----------------|---------------------|
| `injected` | Healthy. Continue. |
| `none` | No signal (context-light phase, e.g. scout bootstrap). Continue. |
| `fallback` | **Cache miss detected.** The Critical Context Forwarding block was incomplete or absent — likely cause: prior context compaction. |

When `fallback` is reported:

1. Re-read `.ai-team/changes/{change_name}/state.yaml` and any envelopes from prior phases stored under `.ai-team/changes/{change_name}/envelopes/` (if present).
2. Rebuild the cached flag set from scratch (Critical Context Forwarding table).
3. Inject the rebuilt block in **all subsequent delegations** for this session.
4. Surface a single warning to the user: `"Detected cache miss in {phase} (context_resolution: fallback) — reloaded session state. Subsequent phases will run with full context."`

This is a self-healing mechanism. Do NOT ignore `fallback` — silent degradation is exactly what this loop is designed to prevent.

### Non-SDD Delegation

For medium tasks that benefit from delegation but don't warrant full SDD:

- Use `model: "sonnet"` (the default tier)
- Include relevant project context (`.ai-team/config.yaml`, applicable skills)
- Give clear instructions on what to do and what files to touch
- Request a brief result summary, not a full envelope

```
Agent({
  description: "{brief task description}",
  subagent_type: "general-purpose",
  model: "sonnet",
  prompt: `
{Clear task description with file paths and expected outcome}

## Project Context
{Relevant config, conventions, constraints}

When done, report: what you changed, what you tested, any issues found.
Include model_used in your response.
`
})
```

### Delegating to sdd-security

When invoking the security gate, set `mode:` in the Injected Context block.

**For threat-model** — invoke after proposal approval, before spec/design:

```
Agent({
  description: "sdd-security: threat-model for {change-name}",
  subagent_type: "general-purpose",
  model: "opus",
  prompt: `
You are the sdd-security executor.
Do this phase's work yourself. Do NOT delegate or launch sub-agents.
Do NOT search for SKILL.md files or skill registries — your full instructions are pasted inline.

## Injected Context (from orchestrator)
change_name: {name}
change_dir: .ai-team/changes/{name}
model_alias: opus
mode: threat-model
proposal_path: .ai-team/changes/{name}/proposal.md
project_root: {abs-path}
security_touchpoints:
  - {slug}
  - {slug}

## Instructions
{paste skills/sdd-security/SKILL.md}

## Shared Protocols
{paste context-protocol.md, persistence-contract.md, result-envelope.md, spec-convention.md, evidence-protocol.md}

## Task
Run mode threat-model. Read the proposal at proposal_path. For each touchpoint in security_touchpoints,
walk the codebase to identify security-relevant surfaces. Apply the 5-category audit prompt. Produce
threat-model.md and the security_requirements: block in the envelope.

## Project Root
{abs-path}

## Expected Output
Result envelope per result-envelope.md plus the sdd-security extensions (mode, findings, security_requirements, verdict, suppressed_count).
  `
})
```

**For code-audit** — invoke after apply, before verify:

```
Agent({
  description: "sdd-security: code-audit for {change-name}",
  subagent_type: "general-purpose",
  model: "sonnet",
  prompt: `
You are the sdd-security executor.
Do this phase's work yourself. Do NOT delegate or launch sub-agents.
Do NOT search for SKILL.md files or skill registries — your full instructions are pasted inline.

## Injected Context (from orchestrator)
change_name: {name}
change_dir: .ai-team/changes/{name}
model_alias: sonnet
mode: code-audit
tasks_path: .ai-team/changes/{name}/tasks.md
proposal_path: .ai-team/changes/{name}/proposal.md
project_root: {abs-path}
change_branch: {branch}
base_branch: {base}

IMPORTANT — base_branch semantics (DR-10): base_branch MUST be the merge-base of the change branch
relative to main, NOT simply "main". Use `git merge-base main {change_branch}` to compute it.
Injecting "main" directly reads the entire history since the branch diverged and inflates the diff scope.
Compute the merge-base once and pass the resulting SHA as base_branch.

## Instructions
{paste skills/sdd-security/SKILL.md}

## Shared Protocols
{paste context-protocol.md, persistence-contract.md, result-envelope.md, spec-convention.md, evidence-protocol.md}

## Task
Run mode code-audit. Run `git diff {base_branch}..{change_branch}` to identify changed files.
Read each. Read up to 10 1-hop callers for reachability context. If config.yaml declares
test_commands.security, invoke it. Apply the 5-category audit prompt to the diff. Produce
audit-report.md.

## Project Root
{abs-path}

## Expected Output
Result envelope per result-envelope.md plus the sdd-security extensions (mode, findings, verdict, suppressed_count).
  `
})
```

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
