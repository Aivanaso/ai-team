# Edge Cases — sdd-spec

## Domain Needs Baseline (existing code, no spec)

If an affected domain has existing code but no base spec:

- Skip that domain — generate delta specs only for domains with changes.
- Generate deltas for all other domains that are ready.
- Return `status: warning` (not `blocked`) with the domains needing baselines listed in `risks`.
- The orchestrator will trigger baseline generation and re-run the spec phase for the remaining domains.

Why `warning` and not `blocked`: partial work is better than no work. Don't discard ready domains.

## Greenfield Domain

If the proposal introduces a domain that doesn't exist in the codebase:

- Generate a **full spec** (not a delta) — there's no base to diff against.
- Use the template from `references/base-spec-template.md`. Start IDs at `001`.
- This full spec becomes the base spec when archived.
- Mark it clearly in the result envelope: `type: full` in the artifact entry.

## AC Spans Many Domains

If a single acceptance criterion requires changes in 3+ domains:

- Create a requirement in each domain with cross-references.
- The primary domain gets the "main" requirement; other domains get supporting requirements that reference it.
- Use the `Cross-ref` field to link bidirectionally — if `REQ-AUTH-008` references `REQ-USERS-015`, then `REQ-USERS-015` references `REQ-AUTH-008`.

## Proposal Has Conflicting ACs

If two acceptance criteria contradict each other:

- Document the conflict as a risk in the result envelope.
- Surface it via `status: needs_input` with the specific conflict described; the user decides.
- Generate specs for the non-conflicting ACs normally.

## Vague or Unverifiable AC

If an AC is too vague to decompose into requirements even after proposal approval:

- Flag it in the result envelope as a risk with exact AC text.
- If ALL ACs are vague, return `status: needs_input`.
- If only some ACs are vague, generate specs for the clear ones and return `status: warning`.

## Unverifiable Scenario Detail

If a scenario depends on behavior you couldn't verify from reading the code:

- Mark the scenario with `[unverified]` inline.
- Continue — do not block on unverifiable details.
- List the unverified items in `risks` in the envelope.

## Missing `change_type` in Injected Context

If `change_type` is missing from the injected context:

- Read `.ai-team/changes/{change-name}/state.yaml` to recover it.
- Report `context_resolution: fallback` in the envelope.
- List `change_type` under `risks` as recovered value.

## `skip_spec: true` Received

If the orchestrator sends `skip_spec: true` (infra short path):

- Return immediately with `status: ok` and `executive_summary: "spec skipped — infra change"`.
- Leave `state.yaml` spec phase status unchanged (spec was skipped, not completed).
- Skip writing spec artifacts.
