---
name: sdd-propose
description: "Trigger: orchestrator launches propose for new SDD change. Translate user intent into RFC-style proposal grounded in codebase."
disable-model-invocation: true
user-invocable: false
---

## Activation Contract

Run when the orchestrator launches the propose phase for a new SDD change. Produce: `proposal.md` (RFC-style) grounded in codebase analysis, updated `state.yaml`. Never write application code. Never modify files outside `.ai-team/changes/{change-name}/`.

## Hard Rules

- Follows common rules: read-only on app code, write-scope, envelope-always — see `_shared/common-rules.md`.
- Proposal is strategic, not technical: no file names, no class designs, no schemas in the Approach section.
- Ground every claim in user input or code analysis. No hallucinated features.
- Surface conflicts, never silently resolve them. For open questions, always include a grounded recommendation.
- Bounded exploration: Phase A free (glob/grep), Phase B budgeted (20-40 file reads by complexity).

## Decision Gates

| Condition | Action |
|---|---|
| Request is too vague to derive 2+ testable ACs | Return `status: needs_input` per [references/edge-cases.md](references/edge-cases.md). |
| Request contradicts existing spec or code | Document in Risks; set `status: warning`. |
| Proposal spans 5+ domains | Flag splitting in Risks; proceed with the single proposal. |
| No `.ai-team/specs/` exists | Proceed; mark domains as "no baseline spec". |
| User journey passes through incompatible existing flow | Add that domain to Affected Domains with required changes. |
| `proposal.md` already exists for change-name | Return `status: blocked`. |
| Rule 4 trigger detected in request or draft | Run invariant greps before finalising proposal (see Step 4c). |
| Rule 5 trigger detected (cross-repo citation) | Run precondition check before finalising proposal (see Step 4d). |

## Execution Steps

1. Read startup files: `_shared/context-protocol.md`, `_shared/persistence-contract.md`, `_shared/result-envelope.md`, `_shared/evidence-protocol.md`.
2. Check Decision Gates: vague, blocked, or duplicate — return early if triggered.
3. Parse user request: extract core intent, explicit constraints, implicit assumptions.
4. Identify affected domains: grep keywords, map to business domains using `config.yaml` architecture hints.
5. Check existing specs: read `.ai-team/specs/{domain}/spec.md` for each affected domain; note gaps.
6. Phase A (free): glob directory tree, grep for imports/decorators/routes related to the change. Build dependency sketch.
7. Phase B (budgeted): read entry points, trace code flow, identify constraints and conflicts. **Budget:** 20 reads (single domain, known arch) / 30 (multiple domains) / 40 (unknown arch or legacy).
8. Step 4b — User Journey Check: if feature has frontend scope, walk each user path end-to-end through existing flows. Detect incompatible assumptions in flows not otherwise in scope.
9. Step 4c — Rule 4 (Validate Assumed Invariants): if the request or draft mentions a lexical signal (`todos`, `todas`, `siempre`, `nunca`, `convención`, `all`, `every`, `always`, `never`, `consistent`, `uniform`, or "all X follow Y"), the invariant must be validated before writing the proposal. State the invariant in one sentence. Run ≤ 5 greps (cheapest first, stop on counter-examples). If counter-examples exist: add `high` severity risk + Open Question with two paths. If clean: add `Invariant validated:` note in the relevant section.
10. Step 4d — Rule 5 (Cross-Repo Pattern Transplant): if the request or draft cites a sibling repo (`como hace {repo}`, `mirror of {repo}`, path crossing repos), verify all 5 axes before adopting the pattern: **build topology** / **dependency layout** / **framework version** / **runtime topology** / **environment scope**. Decide `proceed` / `adapt` / `reject`. Record in Risks (adapt/reject) or Approach inline note (proceed).
11. Step 4e — Classify Change Type: pick `infra`, `feature`, or `mixed`. Self-check: (1) any user-visible ACs? (2) any business rule/data change? (3) any existing REQ-ID modified? (4) all domains impact `refactor`? All yes → `infra`. Any doubt → `mixed`. Record in proposal.md Change Type section AND envelope `change_type`.
12. Step 4f — Classify Security Sensitivity: walk the 9 touchpoints; emit matching slugs as `security_touchpoints`. If none match, emit `security_touchpoints: []` — explicit empty list, NOT omitted. An omitted field is ambiguous; an explicit empty list signals the classification ran and found nothing. Bootstrap clause: if this propose run IS the change that introduces the touchpoint classification step itself, fill `security_touchpoints` manually from the drafted Security Sensitivity section.

    Touchpoints:
    - `auth/authz` — login, permissions, roles, API tokens, session, JWT
    - `crypto` — encryption, hashing, signing, certificates, randomness, secrets
    - `deserialization` — JSON/XML/YAML parsing of untrusted input, `unserialize`, pickle
    - `file-io-uploads` — file uploads, downloads, path manipulation
    - `network-ssrf` — outbound HTTP from server, URL fetching, webhooks
    - `db-direct-input` — raw SQL, query builder with user input, NoSQL queries with user input
    - `new-dependencies` — new library/package not currently in the project
    - `env-secrets` — env vars, secrets, API keys, credentials, `.env`, vault
    - `regex-external-input` — regex matching against user-supplied strings

    Note: `auth/authz` uses a slash (locked by spec Scenario P1.1). Other 8 slugs use dashes.

13. Write `proposal.md` using [references/proposal-template.md](references/proposal-template.md). Run Scope-AC Coverage Check: walk In Scope line by line; every item must have ≥ 1 AC.
14. Update `state.yaml`: `propose.status → done`, `propose.completed → ISO 8601`, `propose.agent → sdd-propose`, `updated → now`.
15. Return envelope per [references/envelope-examples.md](references/envelope-examples.md). Set `change_type` and `security_touchpoints` fields.

## Output Contract

Write `.ai-team/changes/{change-name}/proposal.md`. Update `state.yaml` (status → done, completed → ISO 8601, agent → sdd-propose). Return envelope with `status`, `executive_summary`, `change_type`, `security_touchpoints`, `artifacts`, `next_recommended`, `model_used`, `context_resolution`. Omit `spec` from `next_recommended` when `change_type: infra` (orchestrator may skip spec).

## References

- [references/proposal-template.md](references/proposal-template.md) — load when writing proposal.md (Step 13).
- [references/envelope-examples.md](references/envelope-examples.md) — load when building result envelope (Step 15).
- [references/edge-cases.md](references/edge-cases.md) — load when a Decision Gate triggers (vague/conflicting/massive/no-specs/incompatible-flow/duplicate).
- `../_shared/context-protocol.md` — startup sequence.
- `../_shared/persistence-contract.md` — write rules and state.yaml schema.
- `../_shared/result-envelope.md` — envelope schema and canary fields.
- `../_shared/evidence-protocol.md` — Rule 4 (invariant greps) and Rule 5 (cross-repo transplant check) full procedures.
- `../_shared/spec-convention.md` — load when reading existing specs to cross-reference REQ-IDs.
