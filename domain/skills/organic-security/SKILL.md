---
name: organic-security
description: "Trigger: orchestrator launches threat-model over a design file (ticket security-threat-model) or code-audit on a tier-2 phase candidate (ticket security-audit)."
disable-model-invocation: true
user-invocable: false
---

## Activation Contract

Two moments, two modes. **threat-model** (before the design is approved): the input is the
design FILE (`.ai-team/designs/<task>.md`, one page, no diff); read its objective, surfaces,
external conditions and decisions, walk the touchpoints, and return MUST/SHOULD security
requirements the orchestrator copies into the design's `## Seguridad` as decisions. **code-audit**
(tier 2, after an implementer attempt): the input is the phase candidate (`group_files`), the
phase file and the design's `## Seguridad`; verify that every security measure the design
decided is implemented, then audit the diff with the five categories; the report's final
fenced ```json block is a security-fragment receipt the machine validates at settle time.
Read application code to find vulnerabilities; never modify it.

## Hard Rules

- Follows common rules: read-only on app code, write-scope, envelope-always, seniority — see `_shared/common-rules.md`.
- Writes only the report at the injected `report_destination` (a FILE path ending in `.md`).
- Every finding cites `file:line` (Rule 1); in threat-model mode a requirement cites the design line or surface it protects. Uncited candidates are dropped and named in `risks`.
- Report every finding, uncertain or minor included, each with `confidence` and `severity`; in code-audit also `evidence: executed | read` and a `trigger` when `read` and MAJOR/CRITICAL (else MINOR at most). Low confidence never lowers a severity.
- Code-audit: a `## Seguridad` measure not implemented is a CRITICAL finding (`read`, trigger = the measure text); a measure implemented differently from what the design decided is a MAJOR. -- because the threat-model's measures entered the design as decisions the user approved.
- Threat-model: a fragile invariant ("safe today because a cleanup happens to run") becomes a MUST/SHOULD requirement so the design owns a structural guard, or the user accepts the risk explicitly.
- The nine touchpoint slugs (verbatim): `auth/authz`, `crypto`, `deserialization`, `file-io-uploads`, `network-ssrf`, `db-direct-input`, `new-dependencies`, `env-secrets`, `regex-external-input`.
- No commit-blocking verdict of its own: the fragment carries no `verdict`; the machine derives blocked from any CRITICAL in `lenses.security` at commit-check.
- Receipt self-validation in code-audit, every pass: `skills/_shared/scripts/ai-team receipt check {report_destination} .`; fix every VIOLATION; record command, exit code and fixes in `## Receipt Self-Validation`.
- One report, one block (code-audit): every other JSON excerpt is fenced ```text. Threat-model writes no json block at all.
- Read-only auditor: no state-changing git commands.

## Decision Gates

| Condition | Action |
|---|---|
| `mode` missing or not `threat-model` / `code-audit` | `status: blocked`, "Invalid mode: '{value}'." |
| `mode: threat-model` AND `design` absent or unreadable | `status: blocked`, cite the path. |
| `mode: threat-model` AND the design's `security` frontmatter is not `pending` | `status: warning`, still run; note it in `risks` (the orchestrator decides). |
| `mode: code-audit` AND `group_files` or `phase_file` missing | `status: blocked`, name the field. |
| `mode: code-audit` AND `group_files` empty or none exist | `status: ok`, `lenses.security.status: pass`, "no candidate changes to audit". |
| `report_destination` absent | `status: blocked` — the report is the product. |
| `security_touchpoints` absent (threat-model) | infer from the design text via the nine slugs; the Temporal Invariant Sweep and the Seam & Failure Sweep run regardless. |
| ≥ 1 CRITICAL, any confidence | `lenses.security.status: findings`, base `status: warning`. |
| 0 CRITICAL, ≥ 1 MAJOR/MINOR | `status: findings`, base `ok`. |
| 0 findings | `status: pass`, base `ok`. |

## Execution Steps

### Mode threat-model

1. Read `_shared/context-protocol.md`, `_shared/persistence-contract.md`. Validate `mode`, `project_root`, `design`, `report_destination`, optional `security_touchpoints`.
2. Read the design: `## Objetivo`, `### Superficies nombradas`, `### Condiciones externas a conservar`, `## Decisiones`, `## Fases`. For each surface, read the file at the cited line and its 1-hop callers.
3. For each triggered touchpoint apply the five categories (input validation / auth+authz / crypto+secrets / injection+RCE / data exposure — [references/worked-examples.md](references/worked-examples.md)).
4. Temporal Invariant Sweep: temporal fields the design or its schemas name; rejection semantic per field; every read path; a read path deciding auth/access/state without the check is a finding.
5. Seam & Failure Sweep: failure mode per call site, interleaving per mutated field, crash window per multi-store sequence.
6. Write the report at `report_destination` per [references/threat-model-template.md](references/threat-model-template.md): summary, touchpoints, findings, both sweeps, and `## Security requirements` — one MUST/SHOULD line each, phrased as an invariant the design can adopt verbatim, with the surface it protects. No json block; a one-line "no receipt block in this mode".
7. Return the envelope.

### Mode code-audit

1. Read the protocols. Validate `mode`, `project_root`, `design`, `phase_file`, `group_files`, `tier`, `tier_reason`, `report_destination`.
2. Read the design's `## Seguridad` (the measures) and the phase file; resolve and read every `group_files` file in full plus up to 10 1-hop callers; `git -C {project_root}` for any inspection.
3. Read `config.yaml`; run `test_commands.security` if declared, else note "not configured (skipped)".
4. Measures first: for each `## Seguridad` bullet, find its implementation in the candidate (`file:line`) or record the CRITICAL/MAJOR finding the Hard Rules prescribe.
5. The five categories on `group_files`; the enforcement-wiring check (every new guard ships its executor).
6. Write the report per [references/audit-report-template.md](references/audit-report-template.md): the six category sections, `## Security measures` (implemented / missing), `## Receipt Self-Validation`, and `## Receipt` with the single ```json block `{ "kind": "security-fragment", "tier", "tier_reason", "lenses": { "security": { "status", "findings" } } }`. Self-check with `skills/_shared/scripts/ai-team receipt check {report_destination} .` until exit 0.
7. Return the envelope.

## Output Contract

```yaml
status: ok | warning | blocked
executive_summary: "..."
mode: threat-model | code-audit
artifacts: [{ name: "report", path: "<report_destination>" }]
security_lens:                   # code-audit: the same object the report's block carries under lenses.security
  status: pass | findings
  findings_count: { CRITICAL: 0, MAJOR: 0, MINOR: 0 }
security_requirements: []        # threat-model only — [{ level: MUST | SHOULD, text: "<invariant>", protects: "<surface, file:line>" }]
next_recommended: []
risks: []
model_used: "sonnet"
context_resolution: self-loaded | fallback | none
```

## References

- [references/threat-model-template.md](references/threat-model-template.md) — threat-model report template; load at threat-model Step 6.
- [references/audit-report-template.md](references/audit-report-template.md) — audit report template and the enforcement-wiring category; load at code-audit Step 6.
- [references/worked-examples.md](references/worked-examples.md) — temporal sweep retrospective and the five categories in full.
- [references/envelope-examples.md](references/envelope-examples.md) — envelopes for both modes.
- [references/edge-cases.md](references/edge-cases.md) — no touchpoints, all low-confidence, empty group_files, invalid mode, re-audit.
- `../_shared/result-envelope.md` — Review Receipt schema (`lenses.security` shape, `kind: security-fragment`).
- `../_shared/machine.md` — how the machine consumes the fragment at settle and commit-check.
- `../_shared/context-protocol.md`, `../_shared/persistence-contract.md`, `../_shared/common-rules.md`, `../_shared/evidence-protocol.md` (Rule 1).
