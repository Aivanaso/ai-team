# Edge Cases — sdd-design

## No Delta Specs Available

If the spec phase hasn't completed yet (parallel execution or `skip_spec: true`):

- Design from the proposal's acceptance criteria and your code analysis.
- Note in the design document: "Designed from proposal ACs — delta specs not yet available. Review for alignment when specs complete."
- This is valid — the proposal has enough information for technical design.
- On infra short path (`skip_spec: true`), this is the expected path, not a fallback.

## Trivial Change

If the change is small enough that a full design document would be overkill (e.g., adding a single field to an entity):

- Still write a design.md, but keep it minimal — just the component changes and data model.
- Omit sections that don't apply (no API contracts if no API changes, no test strategy if obvious).
- Return envelope with a note: "Minimal design — change is straightforward."

## Conflicting Patterns in Codebase

If the codebase has inconsistent patterns (e.g., some modules use repository pattern, others access ORM directly):

- Follow the most recent or most common pattern.
- Document the inconsistency as a design decision: "Followed pattern X because {reason}, but noted pattern Y also exists."
- Surface it as a risk in the result envelope; the orchestrator decides whether to scope a separate refactoring change.

## Stack Mismatch

If the proposal requires something the current stack doesn't support (e.g., "add real-time notifications" but no WebSocket library exists):

- Design the solution including any new dependencies needed.
- List new dependencies explicitly in the design with version recommendations.
- Flag as a risk: "Introduces new dependency: {package}. Verify compatibility with existing stack."
