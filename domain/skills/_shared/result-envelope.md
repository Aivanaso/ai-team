# Result Envelope

> Structured return format for all sub-agent responses.

## Purpose

Every sub-agent MUST return results in this format. The orchestrator ingests ONLY the envelope — it never reads full artifact contents. This keeps the orchestrator's context lean and focused on coordination.

## Format

```yaml
status: ok | warning | blocked | failed
executive_summary: "1-3 sentence summary of what was done and key findings"
artifacts:
  - name: "proposal"
    path: ".ai-team/changes/user-auth/proposal.md"
  - name: "config"
    path: ".ai-team/config.yaml"
next_recommended:
  - "spec"
  - "design"
risks:
  - "Optional: any concerns or blockers discovered"
```

## Field Reference

### `status` (REQUIRED)

| Value | Meaning | Orchestrator action |
|-------|---------|-------------------|
| `ok` | Task completed successfully | Proceed to next phase |
| `warning` | Completed but with concerns | Show risks to user, proceed with caution |
| `needs_input` | Cannot proceed — user input is too vague or incomplete | Show questions to user, re-run agent with clarified input |
| `blocked` | Cannot proceed — missing dependency or technical blocker | Ask user for resolution |
| `failed` | Unrecoverable error | Report to user, suggest retry or alternative |

### `executive_summary` (REQUIRED)

- 1-3 sentences maximum
- Written for the orchestrator, not the user (technical, precise)
- MUST include the key outcome — what changed, what was decided
- Example: `"Detected React 19 + TypeScript + Vitest stack. Generated config.yaml with 3 custom rules from existing ESLint config. No SKILL.md files found in project."`

### `artifacts` (REQUIRED, may be empty)

- List of files created or modified during the task
- Each entry has `name` (human-readable identifier) and `path` (relative to project root)
- Empty array `[]` is valid (e.g., for pure exploration tasks that only return a summary)

### `next_recommended` (REQUIRED, may be empty)

- Suggested next phases or actions
- The orchestrator uses this as a hint, not a command
- Must reference valid phase names from the orchestrator's dependency graph

### `questions` (OPTIONAL)

- List of specific questions the agent needs answered before it can proceed
- Used with `status: needs_input` — the orchestrator surfaces these to the user
- Each question should be concrete and actionable, not generic
- Omit entirely if there are no questions

### `risks` (OPTIONAL)

- List of concerns, blockers, or technical debt discovered
- Orchestrator surfaces these to the user when relevant
- Omit entirely if there are no risks

### `model_used` (REQUIRED)

- The model alias this sub-agent ran on (e.g., `"sonnet"`, `"opus"`, `"haiku"`)
- Passed by the orchestrator in the prompt — report it back for traceability

### `context_resolution` (REQUIRED)

Compaction canary. Every sub-agent MUST report whether it received its expected context inputs from the orchestrator's delegation prompt, or had to recover them by itself.

Each SKILL.md declares an "Expected Context (injected by orchestrator)" list. At launch, the sub-agent checks whether all those inputs arrived in the prompt:

| Value | Meaning | What it tells the orchestrator |
|-------|---------|-------------------------------|
| `self-loaded` | Injected Context YAML received; SKILL.md and shared protocols read from disk per References section | Healthy — disk-read delegation worked correctly |
| `injected` | All expected context inputs were present in the prompt (legacy — when orchestrator inlined SKILL.md + protocols) | Healthy — backward-compatible with inline delegation |
| `fallback` | One or more expected inputs were missing; the sub-agent recovered them by reading `.ai-team/changes/{change}/` directly | Cache miss — orchestrator likely lost state (compaction). Re-read state and re-inject in subsequent delegations |
| `none` | No expected inputs declared for this phase, or the sub-agent had nothing to verify | No signal — phase is context-light (e.g., scout bootstrap) |

The orchestrator inspects this field on every return. See `sdd-orchestrator-protocol.md` → "Context Resolution Feedback" for the self-correction rule.

**Rule for sub-agents**: do not lie. If you read a path that the orchestrator should have given you, report `fallback` and list which inputs were missing in `risks`. Silent fallback defeats the canary.

### `execution_evidence` (OPTIONAL globally; REQUIRED for `sdd-apply`)

Captures the literal stdout of verify commands and created test files, so the orchestrator can independently confirm apply ran them. Skills where this field is REQUIRED: `sdd-apply` (extensible — other skills may add it without breaking the schema).

```yaml
execution_evidence:
  typecheck:               # include only if config.yaml declares a typecheck command
    command: "<verbatim command from config.yaml>"
    exit_code: <int>
    last_lines: |
      <last ~15 lines of stdout, truncated>
  lint:                    # include only if config.yaml declares a lint command
    command: "<verbatim command from config.yaml>"
    exit_code: <int>
    summary: "<one-line digest, e.g. error/warning/info counts as reported by the tool>"
  tests_created:           # one entry per test file created during this apply run
    - file: "<path/to/created/test/file>"
      command: "<command that runs THIS file only, derived from config.yaml runner conventions>"
      exit_code: <int>
      passed: <int>
      failed: <int>
```

**Rules:**
- If `config.yaml` does not declare a typecheck or lint command, omit the corresponding sub-block (do not leave it empty). Cite the omission in `executive_summary`.
- All commands are read verbatim from the project's `config.yaml`. The schema does NOT name any specific tool, package manager, or test runner — those are project-level concerns.
- Apply MUST populate this field before composing the envelope. An empty or absent `execution_evidence` in an apply envelope is a contract violation (equivalent to `status: ok` with no evidence).

### `deviation_report` (OPTIONAL globally; REQUIRED for `sdd-apply` with `status: blocked`)

Structured block apply emits when a deviation from `tasks.md` is required and apply cannot
self-resolve. Replaces the legacy "apply writes `decisions[]`" path: apply surfaces the
deviation; the orchestrator decides the action and authors the audit-trail entry.

```yaml
deviation_report:
  kind: out-of-plan | design-pivot | test-orphan       # REQUIRED — one of the three exact values
  task_ref: "<task-id-from-tasks.md>"                   # REQUIRED — the task in scope when the deviation surfaced
  evidence:                                              # REQUIRED — factual evidence (Evidence Protocol Rule 1)
    file: "<path or null>"
    line: <int or null>
    command: "<verbatim command or null>"
    output: "<last-15-lines or null>"
  suggested_action: "re-engage-tasks | re-engage-design | re-engage-apply-refined | escalate-user"
```

**Multiplicity:** single per envelope. Apply blocks at the FIRST deviation it encounters;
subsequent task processing in the same run is skipped. Rationale: a single deviation triggers
an orchestrator round-trip; accumulating multiple deviations adds parsing complexity without
benefit.

**Required fields:** `kind`, `task_ref`, `evidence` (at least one of `evidence.file`/
`evidence.command` populated), `suggested_action`.

**Rules:**
- Apply MUST populate `deviation_report` whenever it returns `status: blocked` with a structured
  deviation. Absent or empty `deviation_report` on a `status: blocked` apply envelope is a
  contract violation (orchestrator falls back to "escalate-user").
- Populate `deviation_report` only when returning `status: blocked` with a structured deviation (the field is for the blocked path only; omit it on status: ok, warning, or failed).
- Other phases MAY include `deviation_report` if they have a structured block to surface, but
  this is not currently triggered by any phase other than apply.
- The orchestrator translates `deviation_report` into a `decisions[]` entry per the Deviation
  Report Ingestion subsection in `sdd-orchestrator-protocol.md`. Apply does NOT touch `decisions:`.

**Roots-violation case (forwarded `allowed_edit_roots` guard).** When `sdd-apply` is about to
write an application-source file whose target path falls outside the forwarded
`allowed_edit_roots` (REQ-APPLY-024), it emits a `deviation_report` for this case using the
existing `out-of-plan` kind (a roots violation is a subset of an out-of-plan write — no new
kind token). It is distinguished from a generic out-of-plan fix by its `evidence`:
- `kind: out-of-plan`
- `evidence.file`: the attempted target path that fell outside the roots.
- `evidence.output`: the literal note
  `out-of-roots: target '<path>' not within allowed_edit_roots [<root>, <root>, ...]` — so
  both the attempted path and the violated roots set are recoverable from the envelope alone.
- `suggested_action`: `re-engage-apply-refined` (orchestrator widens roots and re-engages) or
  `escalate-user` (orchestrator treats it as scope creep). The orchestrator's widen-or-stop
  decision (REQ-ORCHESTRATOR-017) selects which is acted on.

**Backward-compatibility:** this case adds **no new `kind` token** — the three pre-existing
kinds (`out-of-plan`, `design-pivot`, `test-orphan`) and their `evidence`/`suggested_action`
shapes are unchanged. A parser recognising only those three handles a roots violation
identically to any other `out-of-plan` report.

### `change_type` (OPTIONAL — propose phase only)

- Classifies the change for orchestrator routing decisions
- Values: `infra` | `feature` | `mixed`
  - `infra` — refactor, plumbing, deps, tooling, observability, performance, internal migrations. NO new business requirements, no user-observable behavior changes
  - `feature` — adds or modifies user-observable behavior, business rules, or UX
  - `mixed` — both at once, OR uncertain (default to `mixed` when in doubt)
- The orchestrator uses `infra` to offer skipping the spec phase at the proposal approval gate. `feature` and `mixed` always run spec
- Only the `sdd-propose` envelope sets this; other phases omit it

## Rules

1. **Always return an envelope** — even on failure
2. **Summary over detail** — provide enough context for the orchestrator to act without reading the full detail section
3. **Paths are relative** — always relative to the target project root
4. **No code in envelope** — include outcome, counts, and key risks — reserve code snippets for the detail sections
5. **Honest status** — report `status: warning` or `status: blocked` (return `status: ok` only when all checks pass)

## Examples

### Successful Scout Bootstrap

```yaml
status: ok
executive_summary: "Bootstrapped project config. Detected stack (<frameworks> + <language(s)> + <package manager>). Generated config.yaml."
artifacts:
  - name: "config"
    path: ".ai-team/config.yaml"
next_recommended: []
model_used: "sonnet"
context_resolution: "none"
```

### Blocked Spec Phase

```yaml
status: blocked
executive_summary: "Cannot generate specs — proposal.md references an 'auth' domain but no existing specs were found and the proposal lacks acceptance criteria."
artifacts: []
next_recommended: ["propose"]
risks:
  - "Proposal may need revision before spec work can begin"
model_used: "sonnet"
context_resolution: "injected"
```

### Cache Miss After Compaction

```yaml
status: ok
executive_summary: "Tasks generated for change 'oauth-login'. Read design.md and 2 delta specs from disk."
artifacts:
  - name: "tasks"
    path: ".ai-team/changes/oauth-login/tasks.md"
next_recommended: ["apply"]
risks:
  - "Orchestrator did not inject design_path or spec_paths — recovered by listing .ai-team/changes/oauth-login/. Likely compaction event."
model_used: "sonnet"
context_resolution: "fallback"
```

### Apply Blocked with Deviation Report (Test-Orphan)

```yaml
status: blocked
executive_summary: "Blocked at task T2.3: test scaffold references entity MissingService that does not exist in the system. Apply cannot self-resolve; orchestrator should re-engage sdd-tasks."
artifacts:
  - name: "state"
    path: ".ai-team/changes/feature-x/state.yaml"
tasks_status:
  completed: ["T1.1", "T1.2", "T2.1", "T2.2"]
  partial: []
  skipped: ["T2.3", "T2.4"]
execution_evidence:
  tests_created:
    - file: ".../t2.3.test.ts"
      command: "<runs T2.3 test>"
      exit_code: 1
      passed: 0
      failed: 1
deviation_report:
  kind: test-orphan
  task_ref: "T2.3"
  evidence:
    file: "src/app/feature-x/t2.3.test.ts"
    line: 14
    command: "<test runner cmd for t2.3.test.ts>"
    output: "Cannot find module 'MissingService' from src/app/feature-x/t2.3.test.ts:14"
  suggested_action: "re-engage-tasks"
next_recommended:
  - "orchestrator-audit"
risks:
  - "Test scaffold references entity not in the system; tasks must correct the scaffold or expand scope."
model_used: "sonnet"
context_resolution: "injected"
```
