# Proposal Template

Use this template verbatim when writing `proposal.md`. Fill every section — do not omit.

---

```markdown
# Proposal: {Change Name}

> {One-line summary of what this change does}

## Change Type

**Type:** `infra` | `feature` | `mixed`

**Justification:** {1-2 sentences. For `infra`: confirm no business rules / user-observable behavior change. For `feature`: name the user-visible outcome. For `mixed`: describe both halves.}

## Problem Statement

{What problem does this solve? Why does it matter?
Derived from user input, but rewritten in concrete terms grounded in the codebase.}

## Scope

### In Scope

- {Concrete deliverable 1}
- {Concrete deliverable 2}

### Out of Scope

- {Thing that might seem related but is explicitly excluded}
- {Future enhancement deferred}

## Affected Domains

| Domain | Spec Exists | Impact |
|--------|-------------|--------|
| {domain} | yes/no | new / modify / extend / refactor |

### Domain Details

#### {Domain 1}

**Current state:** {Brief summary from spec or code analysis}
**Proposed change:** {What changes in this domain}
**Existing requirements affected:** {REQ-IDs or "none — new behavior"}

## Approach

{High-level strategy. HOW will this be done at a conceptual level?
NOT technical design — no file names, no interfaces, no data schemas.
Think: "Add OAuth as an alternative auth strategy alongside email/password"
NOT: "Create OAuthService class that implements AuthStrategy interface"}

### Key Decisions to Make

- {Decision 1 that the spec/design phases will need to resolve}
- {Decision 2}

## Acceptance Criteria

Each criterion MUST be observable and testable. If an AC cannot be written as a concrete, observable check, return `status: needs_input` with a clarifying question (vague ACs cannot be verified by sdd-verify).

- [ ] {Criterion 1 — observable, testable}
- [ ] {Criterion 2}
- [ ] {Criterion 3}

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| {Risk from code analysis} | high/medium/low | {Suggested mitigation} |

## Open Questions

For each question, include a brief recommendation based on your code analysis and domain understanding. The user makes the final call, but grounded suggestions accelerate decisions.

- **{Question}** — {Context from code analysis or PRD}. *Recommendation:* {Your suggested answer and why}.
- **{Question 2}** — {Context}. *Recommendation:* {Suggestion}.

## Security Sensitivity

**Touchpoints triggered:** {comma-separated list, or "none"}

**Rationale per touchpoint:**

- **{touchpoint}** — {one-line evidence: where in the proposal the touchpoint surfaced}
- {repeat per triggered touchpoint, or "N/A — no security-sensitive touchpoints detected"}

**Overall classification:** security-sensitive: yes | no

## References

- {Links to relevant existing specs, explorations, or external docs}
```

## Scope-AC Coverage Check

Before finalizing, verify every item in "In Scope" is covered by at least one AC. Walk In Scope line by line:

1. Find the AC(s) that cover each scope item.
2. If a scope item has no matching AC, add one.
3. If a scope item is too vague to produce a testable AC, move it to Out of Scope with a note.

Frontend pages/forms are the typical blind spot: the API AC covers the backend, but the page that calls it needs its own AC.
