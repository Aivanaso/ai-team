# Result Envelope

> Structured return format for all sub-agent responses.

## Purpose

Every sub-agent MUST return results in this format. The orchestrator ingests ONLY the envelope — it never reads full artifact contents. This keeps the orchestrator's context lean and focused on coordination.

## Format

```yaml
status: ok | warning | blocked | failed
executive_summary: "1-3 sentence summary of what was done and key findings"
artifacts:
  - name: "endpoint"
    path: "services/billing/export.py"
  - name: "config"
    path: ".ai-team/config.yaml"
next_recommended:
  - "run the acceptance checks again after the next dependent change"
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

- Suggested next actions (e.g., "re-run this check after the dependent change lands")
- The orchestrator uses this as a hint, not a command
- Free-text, one line per suggestion — this route has no fixed phase vocabulary to reference

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
| `fallback` | One or more expected inputs were missing; the sub-agent recovered them from other injected fields or by reading the target repo directly | Cache miss — orchestrator likely lost state (compaction). Re-derive the flag cache and re-inject in subsequent delegations |
| `none` | No expected inputs declared for this phase, or the sub-agent had nothing to verify | No signal — phase is context-light (e.g., scout bootstrap) |

The orchestrator inspects this field on every return. See `orchestrator-protocol.md` → "Context Resolution Feedback" for the self-correction rule.

**Rule for sub-agents**: do not lie. If you read a path that the orchestrator should have given you, report `fallback` and list which inputs were missing in `risks`. Silent fallback defeats the canary.

### `skill_resolution` (REQUIRED for delegated workers that consume stack skills, e.g. `organic-implementer`, `organic-scout`)

Skill-injection canary for workers that consume stack skills. The orchestrator forwards matching SKILL.md paths from `.ai-team/skill-registry.md` as a `## Skills to load before work` block; this field reports what actually happened:

| Value | Meaning |
|-------|---------|
| `paths-injected` | Block received; every listed SKILL.md was read in full before writing |
| `path-missing` | Block received but ≥1 listed path is absent on disk — continued without it; missing paths listed in `risks` |
| `none` | No skills block in the prompt — proceeded on `config.yaml` conventions alone |

The orchestrator inspects this field on every return that carries it. See `orchestrator-protocol.md` → "Skill Resolution Feedback".

`organic-implementer` defines its own **bounded** envelope variant (Output Contract in its own
SKILL.md) rather than reusing this base schema verbatim — bounded evidence (`check_results`,
capped digests) instead of a raw-stdout evidence field, and `scope_report` instead of a
structured deviation block. See that skill's Output Contract for its complete field set.

## Review Receipt

Produced by `organic-reviewer` for every candidate Evidence-Tier Review classifies as tier ≥ 1 (schema: `orchestrator-protocol.md` → "Evidence-Tier Review"). Consumed by `work-unit-commits` (commit gate) and the orchestrator (routing, Re-engage Routing on `failure_class`). An absent receipt for a tier ≥ 1 candidate is a hard block on commit — `work-unit-commits` refuses without it.

```yaml
tier: 0 | 1 | 2
tier_reason: "<one line, mandatory — e.g. 'tier 2: modifies session auth middleware'>"
lenses:
  correctness:
    status: pass | findings
    findings:
      - { id: "F-1", severity: CRITICAL | MAJOR | MINOR, file: "<path>", line: <int>, claim: "<one line>" }
  security:                # present only when the diff activated organic-security (tier 2)
    status: pass | findings
    findings:
      - { id: "F-2", severity: CRITICAL | MAJOR | MINOR, file: "<path>", line: <int>, claim: "<one line>" }
verification:
  - { command: "<verbatim>", exit_code: 0, outcome: pass | fail }
overrides:                 # user-accepted findings, if any — omit entirely when empty
  - { finding_id: "F-1", justification: "<user-supplied, one sentence>" }
```

**Rules:**
- `tier_reason` is REQUIRED and non-empty for tier 1 and tier 2 — review cost is never unexplained.
- `lenses.security` is present only when Evidence-Tier Review activated `organic-security` (tier 2); omit it entirely for tier 1.
- Every `findings[]` entry's `claim` MUST resolve to a `file:line` citation — this is the receipt-side half of the Citation audit in `orchestrator-protocol.md` → "Evidence-Tier Review"; a claim without a resolvable citation is a contract violation.
- `overrides` is populated only when the user accepted-and-proceeded over a finding instead of re-engaging the worker; omit the field entirely when no override occurred.
- Tier 0 candidates produce no receipt — the result envelope alone is the record.

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

### Blocked — Scope Exceeds Brief

```yaml
status: blocked
executive_summary: "Cannot implement the billing-export objective without touching services/billing/tax.py, which the Task Brief does not declare."
artifacts: []
scope_report:
  kind: scope-exceeds-brief
  detail: "Export totals require the tax module's rounding helper; not in expected_files."
  target: null
  needed_files: ["services/billing/tax.py"]
next_recommended: ["extend expected_files and allowed_edit_roots, then re-brief"]
risks:
  - "Objective may need a wider brief before implementation can proceed"
model_used: "sonnet"
context_resolution: "self-loaded"
```

### Cache Miss After Compaction

```yaml
status: ok
executive_summary: "Implemented the billing-export endpoint per the Task Brief; both acceptance checks passed."
artifacts:
  - name: "endpoint"
    path: "services/billing/export.py"
next_recommended: []
risks:
  - "Orchestrator did not inject current_iso_utc — recovered via `date -u +%Y-%m-%dT%H:%M:%SZ`. Likely a compaction event."
model_used: "sonnet"
context_resolution: "fallback"
```
