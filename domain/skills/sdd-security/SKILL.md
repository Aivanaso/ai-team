---
name: sdd-security
description: "Trigger: orchestrator launches threat-model after proposal approval (security_touchpoints non-empty), or code-audit after apply. Detect security findings."
disable-model-invocation: true
user-invocable: false
---

## Activation Contract

Run when the orchestrator launches either security gate: `threat-model` mode after proposal approval (when `security_touchpoints` is non-empty), or `code-audit` mode after apply and before verify. Produce `threat-model.md` or `audit-report.md`. Read application code to find vulnerabilities; never modify it.

## Hard Rules

- Follows common rules: read-only on app code, write-scope, envelope-always — see `_shared/common-rules.md`.
- Security artifacts write only to `.ai-team/changes/{change}/` (threat-model.md or audit-report.md). No other paths.
- Every finding cites `file:line` per Evidence Protocol Rule 1. No citation = suppress and tally.
- Confidence threshold > 80%. Suppress uncertain findings; tally every suppression. False positives are worse than missed low-confidence findings.
- Severity vocabulary: `CRITICAL` / `WARNING` / `SUGGESTION` only. Never use HIGH / MEDIUM / LOW.
- Report findings; never fix them. The orchestrator owns the override decision.
- `security_requirements:` block is populated only for `threat-model` mode. For `code-audit`: `security_requirements: []`.

## Decision Gates

| Condition | Action |
|---|---|
| `mode: threat-model` | Run Steps 8.1–8.5 (touchpoint walk + temporal sweep). |
| `mode: code-audit` | Run Steps 9.1–9.5 (diff scan). |
| `mode` missing from context and not recoverable from `state.yaml` | Return `status: blocked`. |
| `mode` is any other value | Return `status: blocked` with "Invalid mode: '{value}'. Expected threat-model or code-audit." |
| `security_touchpoints` is empty (threat-model) | Skip 8.2–8.3; STILL run 8.3.5 temporal sweep. |
| Diff is empty (code-audit) | Return `status: ok`, `verdict: no-findings`. See [references/edge-cases.md](references/edge-cases.md). |
| Finding confidence > 80% | Record finding. |
| Finding confidence ≤ 80% | Suppress; add to tally. |
| `verdict: critical` | Orchestrator shows 3-option override prompt to user. |
| `verdict: warnings-only` or `verdict: no-findings` | No override prompt; pass through silently. |
| User overrides CRITICAL gate | Write `decisions:` entry: `phase: security-threat-model` or `phase: security-code-audit`, `task_ref: "security-override"`, `decision: "User chose to proceed despite [CRITICAL|WARNING] finding [ID]"`, `reason: "[user-provided reason]"`, `evidence: "[finding ID and severity]"`, `commits: []`. |

## Execution Steps

### Mode threat-model (Steps 8.1–8.5)

1. Read `_shared/context-protocol.md` (startup), `_shared/persistence-contract.md` (write rules). Validate injected context: `change_name`, `change_dir`, `mode`, `proposal_path`, `project_root`, `security_touchpoints`. Recover missing fields from `state.yaml`; report `context_resolution: fallback` if needed.
2. Read `proposal.md` at `proposal_path`. For each slug in `security_touchpoints`, identify the proposal section that triggered it.
3. Walk each triggered touchpoint. The nine slugs with classification heuristics:
   - `auth/authz` — login, permissions, roles, API tokens, session, JWT
   - `crypto` — encryption, hashing, signing, certificates, randomness, secrets
   - `deserialization` — JSON/XML/YAML parsing of untrusted input, `unserialize`, pickle
   - `file-io-uploads` — file uploads, downloads, path manipulation
   - `network-ssrf` — outbound HTTP from server, URL fetching, webhooks
   - `db-direct-input` — raw SQL, query builder with user input, NoSQL with user input
   - `new-dependencies` — new library or package not currently in the project
   - `env-secrets` — env vars, secrets, API keys, credentials, `.env`, vault
   - `regex-external-input` — regex matching against user-supplied strings
4. Apply the five audit-prompt categories (see [references/worked-examples.md](references/worked-examples.md) for full detail): input validation / auth+authz / crypto+secrets / injection+RCE / data exposure. Read codebase files to ground findings in specific code locations.
5. Run Step 8.3.5 Temporal Invariant Sweep (transversal — runs always in threat-model mode, even when `security_touchpoints` is empty):
   - **Detect temporal fields** in `proposal.md` and any schema files referenced from the proposal. Match: `*_at` (excluding `created_at`, `updated_at`), `expires_*`, `*_expires_*`, `*_expiry`, `valid_until`, `valid_from`, `not_before`, `not_after`, `consumed_at`, `revoked_at`, `deleted_at`, `deadline`, `ttl`, `*_ttl`.
   - **Identify rejection semantic** per field: `expires_at`/`valid_until`/deadline-style → `now > field`; `not_before`/`valid_from` → `now < field`; `consumed_at` → `IS NOT NULL`; `revoked_at` → `IS NOT NULL`.
   - **Enumerate read paths**: every site that reads each field (SQL WHERE/SELECT, repository methods, guards, middleware).
   - **Verify enforcement**: if any read path consumes the field for an auth/access/state decision without the corresponding check, emit a finding with `category: temporal-invariant-sweep`. Severity CRITICAL when bypass enables privilege escalation, session revival, token reuse, or expired-credential auth; WARNING otherwise.
   - **False-positive guardrails**: suppress if field is purely informational (logging/metrics/display); or check exists but via a non-lexical path (view, DB trigger, RLS); or proposal explicitly reserves the field for a future phase.
   - See [references/worked-examples.md](references/worked-examples.md) for the auth-magic-link retrospective.
6. Write `{change_dir}/threat-model.md` per [references/threat-model-template.md](references/threat-model-template.md). Include: summary, touchpoints triggered, per-touchpoint findings, Temporal Invariant Sweep section (always present), `security_requirements:` block, suppression tally.
7. Update `state.yaml`: `phases.threat_model.status: done`, `completed: {ISO 8601}`, `agent: sdd-security`, `mode: threat-model`. Note: runtime key uses snake_case (`threat_model`); `decisions[].phase` uses kebab-case (`security-threat-model`) — asymmetry is intentional (DD-11).
8. Return envelope per [references/envelope-examples.md](references/envelope-examples.md).

### Mode code-audit (Steps 9.1–9.5)

1. Read `_shared/context-protocol.md` (startup), `_shared/persistence-contract.md` (write rules). Validate injected context: `change_name`, `change_dir`, `mode`, `proposal_path`, `project_root`, `tasks_path`, `change_branch`, `base_branch`.
2. Run `git diff --name-only {base_branch}..{change_branch}` to list changed files. `base_branch` MUST be the merge-base SHA injected by the orchestrator (`git merge-base main {change_branch}`), NOT "main" directly. Read each changed file plus up to 10 1-hop callers.
3. Read `config.yaml`. If `test_commands.security:` exists, run it and capture output. If absent: log "Dependency auditor: not configured (skipped)".
4. Apply the five audit-prompt categories scoped to the diff per [references/worked-examples.md](references/worked-examples.md): input validation / auth+authz / crypto+secrets / injection+RCE / data exposure.
5. Write `{change_dir}/audit-report.md` per [references/audit-report-template.md](references/audit-report-template.md). All 5 category sections MUST be present ("No findings" if clean).
6. Update `state.yaml`: `phases.code_audit.status: done`, `completed: {ISO 8601}`, `agent: sdd-security`, `mode: code-audit`. Note: runtime key `code_audit` (snake_case); `decisions[].phase` is `security-code-audit` (kebab-case) — intentional (DD-11).
7. Return envelope per [references/envelope-examples.md](references/envelope-examples.md).

## Output Contract

Write `.ai-team/changes/{change}/threat-model.md` (threat-model mode) or `.ai-team/changes/{change}/audit-report.md` (code-audit mode). Update `state.yaml` (`phases.threat_model` or `phases.code_audit` → `done`). Return envelope with `status`, `executive_summary`, `mode`, `artifacts`, `findings`, `security_requirements`, `verdict`, `suppressed_count`, `next_recommended`, `risks`, `model_used`, `context_resolution`.

## References

- [references/threat-model-template.md](references/threat-model-template.md) — threat-model.md output template and per-finding structure; load at Step 8 (Step 6 in threat-model mode).
- [references/audit-report-template.md](references/audit-report-template.md) — audit-report.md output template and base_branch semantics; load at Step 9 (Step 5 in code-audit mode).
- [references/envelope-examples.md](references/envelope-examples.md) — envelope variants for both modes (ok/warning/blocked); load when returning the result.
- [references/worked-examples.md](references/worked-examples.md) — auth-magic-link temporal sweep retrospective + five audit-prompt category full detail; load at Step 4 (threat-model) or Step 4 (code-audit).
- [references/edge-cases.md](references/edge-cases.md) — no touchpoints, all-suppressed, empty diff, invalid mode, re-audit; load when an unexpected condition arises.
- `../_shared/context-protocol.md` — startup sequence; load first.
- `../_shared/persistence-contract.md` — write rules, `decisions:` full schema; load at Step 1.
- `../_shared/result-envelope.md` — envelope schema; load when returning the result.
- `../_shared/evidence-protocol.md` — Rule 1 (file:line citation mandatory for every finding).
