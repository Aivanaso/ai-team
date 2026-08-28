---
name: organic-security
description: "Trigger: orchestrator launches code-audit as the tier-2 security lens (group_files), or either mode on user request."
disable-model-invocation: true
user-invocable: false
---

## Activation Contract

Run when the orchestrator launches either security workflow: `code-audit` mode as the tier-2
security lens for a candidate diff (`group_files`), invoked alongside `organic-reviewer` and
merged by the orchestrator into the Review Receipt's `lenses.security`; or either
`threat-model` / `code-audit` mode standalone, on user request, independent of any Task
Brief. Produce the on-disk report AT the injected `report_destination` — a FILE path ending in
`.md`, never a directory — only when that field is injected; always return a `security_lens`
block in the envelope shaped for direct receipt merge. Read application code to find
vulnerabilities; never modify it.

## Hard Rules

- Follows common rules: read-only on app code, write-scope, envelope-always, seniority — see `_shared/common-rules.md`.
- Security artifacts write only to the injected `report_destination`, resolved relative to `project_root` — no fixed `.ai-team/` path exists on this route.
- Every finding cites `file:line` per Evidence Protocol Rule 1 — a finding without a resolvable citation is not recorded, but its drop is never silent — note each uncited candidate in `risks` ("uncited candidate finding dropped: <one-line topic>"). -- because uncited findings are unverifiable and slow down triage; the orchestrator cannot route a fix without knowing exactly where the vulnerability is.
- Report every finding, including ones you are uncertain about or consider low-severity. Do not filter for importance or confidence at this stage — coverage is the goal, and the orchestrator's downstream triage is the filter, not this lens. The evidence axis (below) never narrows this — it governs the SEVERITY a `read`-only finding may carry, never whether a finding is reported. Each finding carries its own `confidence: high | medium | low` alongside `severity`, so the orchestrator can rank.
- In `code-audit` mode (the one merged into the Review Receipt's `lenses.security`), every finding also carries `evidence: executed | read` (`executed` = a command, mutation probe, scenario, or measurement against real data demonstrated the defect; `read` = the finding rests on code reading alone) and an optional `trigger: "<one line>"` naming the concrete input/command/state that reaches the cited line and produces the defect. A `read` finding with no named `trigger` is emitted at MINOR as maximum. The evidence cap applies at emission, before any downstream verdict computation: the confidence rule applies unchanged to the severity actually emitted — low confidence never downgrades an emitted severity. Consequently a CRITICAL or MAJOR with `evidence: read` always carries a `trigger`. `evidence`/`trigger` are N/A in `threat-model` mode — those findings route through `security_requirements`, never into the Review Receipt or the commit gate.
- Severity vocabulary: `CRITICAL` / `MAJOR` / `MINOR` — the Review Receipt's vocabulary (`_shared/result-envelope.md` → Review Receipt); every finding this skill emits uses this vocabulary exclusively.
- The nine security touchpoint slugs (verbatim, `auth/authz` with slash; the other 8 with dashes): `auth/authz`, `crypto`, `deserialization`, `file-io-uploads`, `network-ssrf`, `db-direct-input`, `new-dependencies`, `env-secrets`, `regex-external-input`.
- No independent commit-blocking verdict: this skill returns `security_lens: {status: pass | findings, findings: []}` for the orchestrator to fold into the Review Receipt. `review-clear` / `review-blocked` is `organic-reviewer`'s vocabulary alone — this skill never emits it. Base envelope `status` is `warning` when ≥ 1 CRITICAL finding exists, `ok` otherwise.
- `security_requirements:` is populated only in `threat-model` mode; `code-audit` always returns `security_requirements: []`.
- Fragile invariants get an owner: when threat-modeling identifies an invariant the change depends on that holds only best-effort ("safe today because a cleanup happens to run"), emit a `security_requirements:` entry (MUST or SHOULD) so a follow-up Task Brief implements a structural guard, or the user explicitly accepts the risk. -- because a note without an owner travels session-to-session until it dies unimplemented.
- Read-only auditor: MUST NOT run state-changing git commands (commit, add, push, reset, stash, rm). No `decisions[]` entry — none exists on this route; a user-accepted override is recorded by the orchestrator, not by this skill.

## Decision Gates

| Condition | Action |
|---|---|
| `mode` missing or not one of `threat-model` / `code-audit` | `status: blocked` with "Invalid mode: '{value}'. Expected threat-model or code-audit." |
| `mode: code-audit` AND `group_files` missing | `status: blocked`, names the missing field. |
| `mode: code-audit` AND `group_files` empty or none exist on disk | `status: ok`, `security_lens.status: pass`, note "no candidate changes to audit". See `references/edge-cases.md`. |
| `mode: threat-model` AND `scope_description` missing | `status: blocked`. |
| `security_touchpoints` absent/empty (threat-model) | Infer touchpoints from `scope_description` text via the nine-slug heuristics. STILL run the Temporal Invariant Sweep + Seam & Failure Sweep (transversal, unconditional). |
| Finding identified (any confidence, any severity) | Record it, with its own `confidence` and `severity` — never filter for importance or confidence at this stage. In `code-audit` mode, also tag `evidence: executed \| read`. |
| `code-audit` mode: a finding is `evidence: read` with no named `trigger`, and would otherwise be MAJOR or CRITICAL | Emit it at `severity: MINOR` instead (the evidence cap applies at emission) — still recorded in full, per the coverage rule above. |
| ≥ 1 CRITICAL finding, at ANY confidence level | `security_lens.status: findings`, base `status: warning`. Low confidence never exempts a CRITICAL finding from this row. |
| 0 CRITICAL findings, ≥ 1 MAJOR/MINOR | `security_lens.status: findings`, base `status: ok`. |
| 0 findings at all | `security_lens.status: pass`, base `status: ok`. |

## Execution Steps

### Mode threat-model

1. Read `_shared/context-protocol.md` (startup), `_shared/persistence-contract.md` (write rules — loaded per common-rules Principle 5; this skill writes only when `report_destination` is injected). Validate injected context: `mode`, `project_root`, `scope_description`, `security_touchpoints` (optional), and `report_destination` (always injected for review-plane passes per Critical Context Forwarding — treat absence as degradation: report `context_resolution: fallback` and flag it in `risks`). Report `context_resolution`.
2. For each slug in `security_touchpoints` (injected, or inferred from `scope_description` text per the nine-slug heuristics), identify the passage in `scope_description` that triggered it.
3. Walk each triggered touchpoint, applying the five audit-prompt categories (see [references/worked-examples.md](references/worked-examples.md)): input validation / auth+authz / crypto+secrets / injection+RCE / data exposure. Read codebase files to ground findings in specific locations.
4. Run the Temporal Invariant Sweep (always, transversal): detect temporal fields referenced in `scope_description` and any schema files it points to; identify the rejection semantic per field; enumerate every read path; verify enforcement; emit a finding when a read path consumes the field for an auth/access/state decision without the matching check.
5. Run the Seam & Failure Sweep (always, transversal): failure-mode per call-site, interleaving per mutated field, crash-window per multi-store sequence — mechanics in [references/worked-examples.md](references/worked-examples.md).
6. When `report_destination` is injected, write the report AT that path (it is a FILE path ending in `.md`, e.g. `.ai-team/reviews/YYYY-MM-DD-<slug>-threat-model.md` — never a directory to write a fixed filename into; create its parent directory if absent) per [references/threat-model-template.md](references/threat-model-template.md). Include: summary, touchpoints triggered, per-touchpoint findings, both sweeps (always present), `security_requirements:`. This mode writes no `.json` sidecar — `threat-model` findings carry no `verdict`/`lenses.correctness` and never feed the Review Receipt (Hard Rules); the report includes a one-line "no receipt sidecar in this mode" note instead.
7. Return the envelope per Output Contract.

### Mode code-audit

1. Read `_shared/context-protocol.md`, `_shared/persistence-contract.md`. Validate injected context: `mode`, `project_root`, `group_files`, and `report_destination` (always injected for review-plane passes per Critical Context Forwarding — absence is degradation: report `context_resolution: fallback` and flag it in `risks`). Report `context_resolution`.
2. Resolve each `group_files` path relative to `project_root`; read each in full, plus up to 10 1-hop callers. Scope any git inspection (e.g. `git status`) with `-C {project_root}`.
3. Read `config.yaml` from `project_root`. If `test_commands.security:` exists, run it and capture output; if absent, log "Dependency auditor: not configured (skipped)".
4. Apply the five audit-prompt categories scoped to `group_files` (see [references/worked-examples.md](references/worked-examples.md)): input validation / auth+authz / crypto+secrets / injection+RCE / data exposure. Tag each finding with its own `confidence: high | medium | low`, `severity`, and `evidence: executed | read` (with a named `trigger` when `evidence: read` and severity would otherwise be MAJOR or CRITICAL — the evidence cap then applies before any downstream verdict computation, per Hard Rules).
5. Enforcement wiring check: for every guard the candidate introduces (lint rule, CI step, test gate, pre-commit hook, middleware, validation), verify its executor (workflow step, script entry, registration, route binding) ships in the same candidate. A guard with no executor is a finding (`category: enforcement-wiring`; MAJOR by default, CRITICAL when it is the only control for a CRITICAL threat).
6. When `report_destination` is injected, write the report AT that path (it is a FILE path ending in `.md` — never a directory to write a fixed filename into; create its parent directory if absent) per [references/audit-report-template.md](references/audit-report-template.md). All 6 category sections present ("No findings" if clean). In the same step, write a `.json` sidecar next to it — the identical path with `.md` replaced by `.json` — serializing `{ kind: "security-fragment", tier, tier_reason, lenses: { security: security_lens } }`: the fragment shape of the Review Receipt this lens contributes (the `kind` field is what lets `check-receipt.py` accept this shape without `lenses.correctness`/`verdict` — their absence is never itself the discriminator; no `verdict` field at all, since only `organic-reviewer` computes that field — the orchestrator merges this fragment into the full receipt). Self-check it: `python3 skills/_shared/scripts/check-receipt.py receipt {sidecar path} .`; fix any printed `VIOLATION` line before returning.
7. Return the envelope per Output Contract.

## Output Contract

Writes the report AT the injected `report_destination` — a FILE path ending in `.md`, resolved
relative to `project_root` — mandatory from the orchestrator's side for every review-plane
delegation (`orchestrator-protocol.md` → Critical Context Forwarding); optional only from this
skill's own write step, i.e. it writes nothing when no destination is injected. In `code-audit`
mode, also writes a `.json` sidecar at the identical path with `.md` replaced by `.json` — the
Review Receipt security-lens fragment `{ kind: "security-fragment", tier, tier_reason, lenses: {
security } }`; `threat-model` mode writes no sidecar (Execution Steps). No fixed filename, no
separate `.ai-team/` artifact. Returns:

```yaml
status: ok | warning | blocked
executive_summary: "..."
mode: threat-model | code-audit
artifacts: []                    # only when report_destination was written this run — code-audit: both the .md report and its .json sidecar; threat-model: the .md report only
security_lens:                   # shaped for direct Review Receipt lenses.security merge
  status: pass | findings
  findings:                      # CAP 20 entries — on overflow keep the highest severity-then-confidence entries and note the omitted count in risks ("findings omitted at cap: N")
    - { id: "F-1", severity: CRITICAL | MAJOR | MINOR, confidence: high | medium | low, evidence: executed | read, trigger: "<one line — optional; REQUIRED when severity is MAJOR or CRITICAL and evidence is read>", file: "<path>", line: <int>, claim: "<one line>" }
    # `evidence` and `trigger` are code-audit-mode fields only (Hard Rules); a threat-model-mode finding omits both — they are N/A there, never emitted as `read`
security_requirements: []        # threat-model only; [] for code-audit
next_recommended: []
risks: []
model_used: "sonnet"
context_resolution: self-loaded | fallback | none
```

## References

- [references/threat-model-template.md](references/threat-model-template.md) — threat-model.md output template and per-finding structure; load in threat-model mode when `report_destination` is injected.
- [references/audit-report-template.md](references/audit-report-template.md) — audit-report.md output template and enforcement-wiring category; load in code-audit mode when `report_destination` is injected.
- [references/worked-examples.md](references/worked-examples.md) — temporal-sweep retrospective + the five audit-prompt categories full detail; load at the audit-prompt step in either mode.
- [references/envelope-examples.md](references/envelope-examples.md) — envelope variants for both modes (ok/warning/blocked); load when composing the result.
- [references/edge-cases.md](references/edge-cases.md) — no touchpoints, all findings low-confidence, empty group_files, invalid mode, re-audit; load when an unexpected condition arises.
- `../_shared/context-protocol.md` — startup sequence; load first.
- `../_shared/persistence-contract.md` — write rules (loaded per common-rules Principle 5; this skill writes only when `report_destination` is injected).
- `../_shared/common-rules.md` — consolidated principles (read-only, write-scope, envelope-always, seniority); load at startup.
- `../_shared/result-envelope.md` — Review Receipt schema (`lenses.security` shape); load when composing `security_lens`.
- `../_shared/evidence-protocol.md` — Rule 1 (file:line citation mandatory for every finding).
