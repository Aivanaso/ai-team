---
name: sdd-design
description: "Trigger: orchestrator launches design after proposal approval (and threat-model gate if security-sensitive). Produce technical design grounded in project stack."
disable-model-invocation: true
user-invocable: false
---

## Activation Contract

Run when the orchestrator launches the design phase for an SDD change after proposal approval (and after threat-model gate, if `security_touchpoints` is non-empty). Produce: one `design.md` describing components, data model, API contracts, interactions, test strategy, risks, and design decisions. Never write application code.

## Hard Rules

- Read application code; never modify it.
- Write only `.ai-team/changes/{change-name}/design.md` (plus `state.yaml` update).
- Follow existing project patterns — if the project uses repository pattern, use it. Don't introduce paradigms the proposal doesn't call for.
- Name actual files, classes, interfaces, and methods. Abstract descriptions are not accepted.
- Evidence > Assumption: every framework or project-behavior claim MUST cite a config line or existing caller. See `_shared/evidence-protocol.md`.
- If any design decision cites a sibling repo as the pattern source, apply Evidence Protocol Rule 5 before finalizing — verify all 5 axes (build topology, dependency layout, framework version, runtime topology, environment scope).
- Result envelope always.

## Decision Gates

| Condition | Action |
|---|---|
| `skip_spec: true` (infra short path) | Design from proposal ACs directly; see [references/edge-cases.md](references/edge-cases.md) "No Delta Specs Available". |
| Delta specs not yet written (parallel execution) | Same as above; note in design.md "Designed from proposal ACs". |
| Change is trivial (single field, rename) | Produce minimal design; omit inapplicable sections; note "Minimal design" in envelope. |
| Codebase has conflicting patterns | Follow most recent/common; document inconsistency as a design decision; do NOT fix it. |
| Stack missing a required capability | Include new dependencies; list as risk; see [references/edge-cases.md](references/edge-cases.md) "Stack Mismatch". |

## Execution Steps

1. Read `_shared/context-protocol.md` (startup). Validate injected context; recover missing fields from `state.yaml`; report `context_resolution: fallback` if needed.
2. Read `config.yaml`: stack, architecture style, conventions. Load matched project skills (`nestjs`, `react`, `typescript`, `testing`, etc.).
3. Read proposal, delta specs (if available), and base specs for affected domains.
4. **Phase A — Structural scan (cost-free):** glob and grep to map existing patterns, naming conventions, module structure, shared utilities. Use `config.yaml architecture.style` to focus: `ddd` → aggregates + domain events; `hexagonal` → port interfaces + adapters; `layered/mvc` → controller/service/repository; `modular` → feature folders + module registration.
5. **Phase B — Selective read (budget: 15–25 source files, in priority order):**
   1. An existing feature similar to the one being designed (best design template is the project itself).
   2. Shared base classes, interfaces, abstract types (extension points).
   3. Entity/model definitions for affected domains.
   4. Module registration / dependency injection setup.
   5. Middleware, guards, interceptors, pipes (cross-cutting concerns).
   6. Existing tests for similar features (patterns only; skip individual test cases).
6. Design components per domain: type, exact file path, responsibility (one sentence), key interface (signatures + types, not implementation), dependencies. Follow [references/design-template.md](references/design-template.md) for the full template.
7. Design data model changes: new entities, entity modifications, migrations, indexes. Ground in project ORM conventions.
8. Design API contracts: new/modified endpoints, auth requirements, DTO validation. Follow project conventions from `config.yaml`.
9. Design component interactions: request flow, event flow, error flow — step-by-step sequence.
10. **Cross-repo transplant check (Rule 5):** if any decision cites "mirror of {repo}", "same as {other-repo}", or a path crossing repos — enumerate structural prerequisites, verify each axis, decide `proceed` / `adapt` / `reject`. Embed the citation block in the Design Decisions table. If `reject`, surface in Open Questions with failing axis named.
11. **Side Effects of Topology Decisions (Step 7b):** for any decision touching networking, runtime topology, shared secrets, env vars, or DNS — add an explicit "Side Effects" sub-bullet listing: which namespaces become shared (DNS, env, volumes, secrets); which names could collide; runtime behavior on collision (silent shadow, error, race). The ECO-971 DNS-shadowing incident (joining an external network silently shadowed local services) is the canonical example.
12. Write `design.md` per [references/design-template.md](references/design-template.md).
13. Update `state.yaml`: `phases.design.status → done`, `phases.design.completed → ISO 8601`, `phases.design.agent → sdd-design`, `current_phase → design`, `updated → now`.
14. Return the envelope per [references/envelope-examples.md](references/envelope-examples.md).

## Output Contract

Write `.ai-team/changes/{change-name}/design.md`. Update `state.yaml` (`phases.design.status → done`, `phases.design.completed → ISO 8601`, `phases.design.agent → sdd-design`, `current_phase → design`, `updated → now`). Return envelope with `status`, `executive_summary`, `artifacts`, `next_recommended`, `model_used`, `context_resolution`.

## References

- [references/design-template.md](references/design-template.md) — full design.md template (Context, Component Design, Data Model, API Contracts, Component Interactions, Test Strategy, Design Decisions, Risks, Open Questions); load at Step 6.
- [references/envelope-examples.md](references/envelope-examples.md) — successful, warning, blocked envelope variants; load at Step 14.
- [references/edge-cases.md](references/edge-cases.md) — No Delta Specs Available, Trivial Change, Conflicting Patterns, Stack Mismatch; load when an unexpected condition arises.
- `../_shared/context-protocol.md` — startup sequence; load at Step 1.
- `../_shared/persistence-contract.md` — write rules; load at Step 1.
- `../_shared/result-envelope.md` — envelope schema; load at Step 14.
- `../_shared/evidence-protocol.md` — Rules 1–5 (Rule 5 governs cross-repo transplant; design is the phase most prone to "let's do it like {sibling-repo}").
- `../_shared/spec-convention.md` — when reading delta specs.
