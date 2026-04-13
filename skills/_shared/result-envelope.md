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
- Must reference valid phase names from `config/schema.yaml`

### `questions` (OPTIONAL)

- List of specific questions the agent needs answered before it can proceed
- Used with `status: needs_input` — the orchestrator surfaces these to the user
- Each question should be concrete and actionable, not generic
- Omit entirely if there are no questions

### `risks` (OPTIONAL)

- List of concerns, blockers, or technical debt discovered
- Orchestrator surfaces these to the user when relevant
- Omit entirely if there are no risks

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
executive_summary: "Bootstrapped project config. Detected Next.js 14 + TypeScript + Tailwind + pnpm monorepo. Found 3 existing SKILL.md files (react, typescript, testing). Generated config.yaml and skill-registry.md."
artifacts:
  - name: "config"
    path: ".ai-team/config.yaml"
  - name: "skill-registry"
    path: ".ai-team/skill-registry.md"
next_recommended: []
```

### Blocked Spec Phase

```yaml
status: blocked
executive_summary: "Cannot generate specs — proposal.md references an 'auth' domain but no existing specs were found and the proposal lacks acceptance criteria."
artifacts: []
next_recommended: ["propose"]
risks:
  - "Proposal may need revision before spec work can begin"
```
