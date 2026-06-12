---
name: sdd-spec
description: "Trigger: orchestrator launches spec phase after proposal approval. Write delta specs from proposal ACs."
disable-model-invocation: true
user-invocable: false
---

## Activation Contract

Run when the orchestrator launches the spec phase for an SDD change after the proposal is approved. Produce: delta specs (or full specs for greenfield domains) under `.ai-team/changes/{change}/specs/{domain}/spec.md`. Never modify application code; never produce design or task artifacts.

## Hard Rules

- Follows common rules: read-only on app code, write-scope, envelope-always, seniority — see `_shared/common-rules.md`.
- One delta spec per affected domain — no cross-domain blending. -- ensures the merge algorithm in sdd-archive can apply changes per-domain without cross-contamination.
- Every requirement MUST trace to a proposal AC via `**Source:** AC-{N}`. No orphans.
- Use RFC 2119 keywords (`MUST`, `SHOULD`, `MAY`, `MUST NOT`) for priority fields — no synonyms.
- REQ-ID format: `REQ-{DOMAIN}-{NNN}` — uppercase domain slug, zero-padded three-digit counter. Continue from the highest existing ID in the base spec; never reuse removed IDs.
- Specs are behavioral: describe WHAT the system does, not HOW. No class names, method signatures, or DB column names in requirement text. -- because implementation details in specs couple the spec to a specific design, preventing reuse across alternative designs.
- Every constraint with a quantitative threshold (max/min/range), a qualitative pattern (regex/format/enum), or a refined invariant MUST have at least one Given/When/Then scenario explicitly testing the rejection case at the threshold (e.g., "When value = max + 1, Then reject"). A constraint declared without a boundary scenario is incomplete: downstream phases may implement enforcement that silently no-ops, and the test gap will not surface until a hostile input lands in production. -- ZodPipe bug retro showed that validation took 6 SDDs to surface because boundary rejection scenarios were missing from specs.
- Every requirement describing a user-facing screen or interaction includes a recovery scenario: Given the action fails or its state is lost, Then the user has a visible exit (retry / redirect / link), and degenerate input (zero, empty, reload mid-flow) has defined behavior. This is the interaction counterpart of the boundary-scenario rule above. -- because "the error is surfaced" passes while the user is stranded: a change once shipped 5 confirmed stuck-user defects (dead retry button, silent return, expired session with no redirect) and every one satisfied the written requirements.

## Decision Gates

| Condition | Action |
|---|---|
| `skip_spec: true` in injected context | Return `status: ok`, `executive_summary: "spec skipped — infra change"`. Write nothing. |
| Domain has code but no `spec.md` | Skip that domain. Spec ready domains. Return `status: warning` with missing domains in `risks`. |
| Domain is greenfield (no code, no spec) | Write full spec using `references/base-spec-template.md`; mark `type: full` in envelope. |
| AC is too vague to decompose | Flag in `risks`. If all ACs vague, return `status: needs_input`. |
| `change_type` missing from injected context | Read `state.yaml` to recover; report `context_resolution: fallback`. |
| Cross-domain bidirectional ref missing | Add `Cross-ref` in both requirements before finalising. |

## Execution Steps

1. Read `_shared/context-protocol.md` (startup) and `_shared/spec-convention.md` (spec format). Validate injected context; recover missing fields from `state.yaml` if needed.
2. Read `proposal.md`. Extract ACs, affected domains table, approach, and cross-domain interactions.
3. Read `.ai-team/config.yaml`: stack, architecture style, conventions. (Stack skills are consumed by design/apply via `## Skills to load before work`; specs stay behavioral and need none.)
4. For each affected domain, check whether `.ai-team/specs/{domain}/spec.md` exists. Apply Decision Gates (greenfield / needs-baseline / ready).
5. **Phase A — Structural scan (cost-free):** glob and grep to map domain structure using `architecture.style` hints from config.
   - `ddd` → aggregate roots + domain events in affected bounded contexts
   - `hexagonal` → ports (interfaces) + adapters (implementations)
   - `layered`/`mvc` → controllers, services, entities
   - `modular` → entire feature folder
   - `unknown` → grep domain keywords, cluster by directory
6. **Phase B — Selective reads (budgeted, 10-20 files):** read in priority order: (1) entities/domain models, (2) validation rules (DTOs, validators, guards), (3) service methods, (4) API contracts, (5) cross-domain interfaces. Skip: repository implementations, config files, module declarations, test files (unless verifying ambiguous behaviour), frontend components.
7. Decompose each AC into 1-3 requirements per domain. Assign IDs (continuing from base spec). Set priority (`MUST`/`SHOULD`/`MAY`). Add `Cross-ref` for multi-domain ACs. Write at least one Given/When/Then scenario per requirement — use real field names from step 6 reads.
8. For each ready domain, write the spec artifact per [references/delta-spec-template.md](references/delta-spec-template.md) (delta) or [references/base-spec-template.md](references/base-spec-template.md) (greenfield full spec).
9. Traceability check: every proposal AC covered by ≥1 requirement; every requirement has a `Source` AC; all cross-refs are bidirectional.
10. Update `state.yaml`: `phases.spec.status → done`, `phases.spec.completed → ISO 8601`, `phases.spec.agent → sdd-spec`, `current_phase → spec`, `updated → now`.
11. Return the envelope per [references/envelope-examples.md](references/envelope-examples.md). If any unverified scenarios exist, list them in `risks`.

## Output Contract

Write `.ai-team/changes/{change}/specs/{domain}/spec.md` for each ready domain. Update `state.yaml` (status → done, completed → ISO 8601, agent → sdd-spec). Return a result envelope with `status`, `executive_summary`, `artifacts` (each with `type: delta | full`), `next_recommended`, `model_used`, `context_resolution`.

## References

- [references/delta-spec-template.md](references/delta-spec-template.md) — delta spec Markdown template; load at Step 8.
- [references/base-spec-template.md](references/base-spec-template.md) — base (full) spec Markdown template; load at Step 8 for greenfield domains.
- [references/envelope-examples.md](references/envelope-examples.md) — ok / warning / blocked / needs_input envelope variants; load at Step 11.
- [references/edge-cases.md](references/edge-cases.md) — missing baseline, greenfield, multi-domain ACs, conflicting ACs, unverifiable scenarios; load when an unexpected condition arises.
- `../_shared/context-protocol.md` — startup sequence; load first.
- `../_shared/persistence-contract.md` — write rules.
- `../_shared/common-rules.md` — consolidated principles (read-only, write-scope, envelope-always, seniority); load at startup.
- `../_shared/result-envelope.md` — envelope schema.
- `../_shared/evidence-protocol.md` — Rules 1-5.
- `../_shared/spec-convention.md` — spec format (delta merge algorithm, REQ-ID conventions).
