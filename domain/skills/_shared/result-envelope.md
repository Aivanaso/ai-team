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
| `injected` | All expected context inputs were present in the prompt | Healthy — Critical Context Forwarding worked |
| `fallback` | One or more expected inputs were missing; the sub-agent recovered them by reading `.ai-team/changes/{change}/` directly | Cache miss — orchestrator likely lost state (compaction). Re-read state and re-inject in subsequent delegations |
| `none` | No expected inputs declared for this phase, or the sub-agent had nothing to verify | No signal — phase is context-light (e.g., scout bootstrap) |

The orchestrator inspects this field on every return. See `sdd-orchestrator-protocol.md` → "Context Resolution Feedback" for the self-correction rule.

**Rule for sub-agents**: do not lie. If you read a path that the orchestrator should have given you, report `fallback` and list which inputs were missing in `risks`. Silent fallback defeats the canary.

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
2. **Summary over detail** — the orchestrator doesn't need full context, just the outcome
3. **Paths are relative** — always relative to the target project root
4. **No code in envelope** — never include code snippets in the summary
5. **Honest status** — don't report `ok` if there are unresolved issues; use `warning`

## Examples

### Successful Scout Bootstrap

```yaml
status: ok
executive_summary: "Bootstrapped project config. Detected Next.js 14 + TypeScript + Tailwind + pnpm monorepo. Generated config.yaml."
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
