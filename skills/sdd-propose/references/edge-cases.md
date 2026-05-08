# Edge Cases — sdd-propose

Handling for non-standard inputs. One case per section.

---

## Vague Input

If the user request is too vague to produce concrete, testable acceptance criteria:

- Do NOT produce the proposal.md. Stop and ask the user for clarification.
- Return `status: needs_input` in the result envelope with specific questions about what is unclear.
- The goal is to never pass vague ACs downstream — the spec agent depends on concrete ACs to generate requirements.

What counts as "too vague":
- The request cannot be decomposed into at least 2 observable, testable acceptance criteria.
- Key nouns are undefined (e.g., "improve search" — improve what metric? for which users?).
- The request is a wish, not a goal (e.g., "make it better" vs "reduce search latency below 200ms").

---

## Conflicting Request

If the user's request contradicts existing specs or code behavior:

- Document the conflict explicitly in the Risks section.
- Do NOT silently resolve it — surface it for user decision.
- Set result envelope status to `warning`.
- In Open Questions, offer two resolution paths with a grounded recommendation.

---

## Massive Scope

If the request implies changes across 5+ domains or would be a major rewrite:

- Produce the proposal but add a risk: "Scope may benefit from splitting into multiple changes."
- Suggest domain-by-domain breakdown in the Approach section.
- In Open Questions, ask whether the user wants to split now or treat as one large change.

---

## No Existing Specs

If no `.ai-team/specs/` directory exists or it is empty:

- Proceed normally — the proposal does not depend on existing specs.
- Note affected domains as "no baseline spec" in the Affected Domains table.
- The orchestrator will trigger baseline generation before the spec phase.

---

## Journey Through Incompatible Flow

If a new feature's user journey passes through an existing flow (login, register, onboarding) that has assumptions incompatible with the new context:

- Do NOT mark that domain as "no changes" — it needs changes.
- Add the domain to Affected Domains with the specific modifications needed.
- Add ACs that cover the flow adaptation (e.g., "registration supports account creation without shop creation when redirected from claim flow").
- Add the redirect chain as a testable AC (e.g., "after login/register, user is redirected back to the claim page, not to dashboard").

Real example: a "claim shop" feature assumed the registration flow could be reused as-is. But registration forced shop creation in step 2, and neither login nor register read the `?redirect=` parameter. The claim flow was broken for every new user.

---

## Duplicate Change

If `.ai-team/changes/{change-name}/proposal.md` already exists:

- Return `status: blocked` with message indicating the change already has a proposal.
- The orchestrator should handle this before delegating, but guard against it here too.
