---
name: sdd-tasks
description: "Trigger: orchestrator launches tasks after design (and threat-model gate). Decompose design into ordered task list with PR slicing, test scaffolds, and AC↔test traceability."
disable-model-invocation: true
user-invocable: false
---

## Activation Contract

Run when the orchestrator launches the tasks phase for an SDD change. Produces `.ai-team/changes/{change-name}/tasks.md` — an ordered, grouped implementation plan. Never writes application code. Never modifies source files.

## Hard Rules

- Follows common rules: read-only on app code, write-scope, envelope-always, seniority — see `_shared/common-rules.md`.
- Decompose, don't redesign. Flag disagreements as risks in the result envelope; interface alterations require re-engaging sdd-design (the approved design is the contract for apply). -- because redesigning at the task level invalidates all upstream artifacts (spec, design) and forces re-approval cycles.
- Every task must leave the codebase compilable (or in the meta-project case: leave the framework files in a valid SKILL.md structure). -- because a non-compiling intermediate state prevents apply from running the tests in subsequent tasks.
- Embed enough context in each task that sdd-apply does not need to re-read the full design. -- because apply runs with a fresh context window and no access to design.md; missing context forces apply to guess, which produces semantic drift.
- Evidence > Assumption: cross-repo pattern transplants embed the Rule 5 precondition block per evidence-protocol.
- Declare a test scaffold file per AC in the delta spec, listed in the relevant task's `Files:` block. Emit the AC↔Test Traceability table in tasks.md per REQ-TASKS-019. Meta-project exception (`config.yaml.stack.testing: []`): emit a Manual Review Checklist instead — see Step 7b. -- because without scaffolds declared in Files:, apply invents test structure that may not match the project's patterns or runner discovery paths.
- Number groups sequentially starting at G1 with no gaps. A task belongs to exactly one group. The Execution Order table is the canonical source — see `_shared/common-rules.md` "Logical group" section (REQ-CR-006, REQ-TASKS-021). -- because the Execution Order table is the canonical sequence; gaps cause the orchestrator's task-tracking to miscount progress.

## Decision Gates

| Condition | Action |
|-----------|--------|
| Design has < 5 components, all straightforward | Produce minimal plan (single group, 2-3 tasks). See `references/edge-cases.md`. |
| Task count exceeds 20 | Flag risk "Large task plan ({N} tasks)"; group aggressively; do not block. |
| Severe drift (file deleted, module restructured) | Return `status: warning`; still produce tasks for unaffected parts. |
| Circular dependency between tasks | Merge tasks or introduce a shared types task; never leave cycles in the plan. |
| Cohesion risk is High and no slice plan set | Set `Decision needed before apply: Yes`; assign every task to a feature-level PR slice. |
| `config.yaml.stack.testing` is empty | Emit Manual Review Checklist (REQ-TASKS-020 exception path); set `test_file` cells to `#manual-checklist`, `test_id` to `manual-{AC-N}`. |
| Design introduces a new REQUIRED value (column, env var, constructor param, header, config key) | Run the Step 5b fanout sweep; declare affected fixtures/mocks in the owning task's `Files:` block and the verified-not-affected neighbors in its notes. |

## Execution Steps

1. Read `_shared/context-protocol.md` → startup sequence. Recover missing injected context from state.yaml; report `context_resolution: fallback` in envelope if needed.
2. Read `_shared/persistence-contract.md`, `_shared/result-envelope.md`, `_shared/spec-convention.md`, `_shared/evidence-protocol.md`.
3. Read design.md in full; extract components (name, type, path, action, domain, dependencies). Read delta specs for REQ-IDs and proposal for ACs.
4. **Phase A** (free) — glob/grep every file path the design mentions: verify existing files exist, new files don't, module registrations match.
5. **Phase B** (budgeted, 5-15 files) — read only files where Phase A found discrepancies or where critical interface assumptions need confirmation.
5b. **Required-value fanout sweep:** for every new REQUIRED value the design introduces — DB column, env var, constructor parameter, header, config key — grep ALL fixtures, mocks, factories, and test setups that construct or boot the affected entity/process. Declare each affected file in the owning task's `Files:` block and list the verified-not-affected neighbors in its Implementation Notes ("{TestX} builds {Y} without {value} — no fanout"). -- because the fanout pattern recurs across shapes (a NOT NULL column broke N entity mocks; a required env var broke 34 e2e fixtures) and a pre-grepped fanout list is what keeps apply single-pass and deviation-free.
6. Build component inventory; group into tasks by execution layer (see Layer Ordering below). Assign each task to exactly one group; number groups sequentially from G1. Check compilability after each task in the sequence.
7. **Forecast Review Workload** — classify cohesion risk, propose PR slices, emit the grep contract lines (see Output Contract). Use `references/tasks-template.md` for the full tasks.md structure.
7b. **Test scaffold generation:** If `config.yaml.stack.testing` is non-empty, declare one scaffold file per AC in the delta spec (in the task's `Files:` block) using `references/scaffold-templates.md` dispatch table. Then emit the AC↔Test Traceability table. If `config.yaml.stack.testing: []` (meta-project), emit a Manual Review Checklist table instead with one Bash criterion per AC — see `references/scaffold-templates.md` "Manual Review Checklist Template" section.
8. Map traceability: every REQ must appear in ≥1 task; every AC must trace through ≥1 REQ. Flag gaps as risks. The AC↔Test Traceability table from Step 7b complements this.
9. Write `.ai-team/changes/{change-name}/tasks.md` using `references/tasks-template.md`.
10. Persist: update `state.yaml` (tasks.status → done, completed → ISO 8601, agent → sdd-tasks, current_phase → tasks, updated → now). Return envelope from `_shared/result-envelope.md`.

## Output Contract

### Layer Ordering (mandatory sequence)

| Layer | Content |
|-------|---------|
| 1. Data | Entities + migrations |
| 2. Logic | DTOs + services |
| 3. API | Controllers + module registration |
| 4. Frontend foundation | Type definitions + API client functions |
| 5. Frontend pages | New pages + their components |
| 6. Modifications | Changes to existing files (cross-cutting) |
| 7. Cleanup | Deletions + dead code removal |

### PR Slicing Rule

**1 PR = 1 independent functional feature.** A feature may span N tasks and M files; if all converge on a single deliverable, they go in one PR regardless of line count. Small tasks (<50 lines, no own dependencies) merge into their parent feature. Chained PRs only when PR-2 cannot compile or make sense without PR-1.

Lines are smell, not threshold. A single feature exceeding **~800 estimated lines** is a signal to re-examine whether two features are mixed — not an automatic split order. If after review it is one genuine feature, ship it in one PR.

### Cohesion Heuristics

| Signal | Cohesion risk |
|--------|---------------|
| All tasks belong to a single functional feature, same domain/module | Low |
| One feature crossing 2+ domains but still one logical unit of change | Medium |
| Mix of distinct features, infra + feature work, or breaking changes needing staged rollout | High |

### Grep Contract (verbatim in tasks.md — downstream guards grep these exact strings)

The Review Workload Forecast section of tasks.md MUST contain these lines literally:

```
Cohesion risk: Low|Medium|High
Independent PRs: <count> independent / <count> chained
Decision needed before apply: Yes|No
```

Optional fourth line, emitted only when a single feature exceeds ~800 estimated lines:

```
Size smell: <feature-name> (<N> lines)
```

### Traceability Matrix Schema

The traceability matrix at the end of tasks.md uses this format:

| AC | Requirements | Tasks |
|----|-------------|-------|
| AC-01 | REQ-DOMAIN-001 | 1.1, 2.1 |

### Envelope `review_workload` Block

```yaml
review_workload:
  cohesion_risk: low|medium|high
  features_count: {count}
  independent_prs: {count}
  chained_prs: {count}
  decision_needed_before_apply: true|false
  size_smells:
    - feature: {name}
      lines: {N}
```

## References

- [references/tasks-template.md](references/tasks-template.md) — full tasks.md markdown template; load when writing tasks.md.
- [references/scaffold-templates.md](references/scaffold-templates.md) — test scaffold dispatch table and templates per framework; Manual Review Checklist template for meta-project path; load at Step 7b.
- [references/envelope-examples.md](references/envelope-examples.md) — ok / warning / blocked envelope variants; load when composing the result envelope.
- [references/edge-cases.md](references/edge-cases.md) — trivial change, massive change, no delta specs, drift, no test strategy, circular deps; load when a gate fires.
- `../_shared/context-protocol.md` — startup sequence.
- `../_shared/persistence-contract.md` — write rules.
- `../_shared/common-rules.md` — consolidated principles (read-only, write-scope, envelope-always, seniority); load at startup.
- `../_shared/result-envelope.md` — envelope schema.
- `../_shared/evidence-protocol.md` — Rules 1-5 (interface changes + cross-repo transplants).
- `../_shared/spec-convention.md` — REQ-ID format and delta spec structure.
