# Memory Capture — Reference

> Loaded by sdd-archive Step 1. Contains calibration guidance, output schema, skip conditions, and surfaces commentary.

## Surfaces to Scan

Read the change's `proposal.md`, `design.md`, `tasks.md`, `verification-report.md`, and `state.yaml.decisions:` looking for items under these surfaces:

| Surface | Examples of capture-worthy items |
|---------|----------------------------------|
| **External dependencies** | Forks (PECL, custom GitHub forks), CDN URLs, registry paths, version pins with a load-bearing reason |
| **Environment quirks** | DNS shadowing, network namespace collisions, secret stores, auth-mode edge cases, mysql `caching_sha2_password`, missing system packages |
| **Project conventions discovered** | Auto-migration policy, deploy script structure, CI script gotchas, single-stage vs multi-stage Dockerfiles |
| **Decisions loaded with non-obvious context** | Mid-flight pivots from `decisions:` whose reason will not be discoverable from the resulting code (e.g., "we use `auto_setup: true` because the AMQP transport lazy-declares queues anyway") |
| **Smoke/canary mechanisms** | Health endpoints, ping commands, debug flags created during the change that should survive long-term |
| **Security findings worth remembering** | Project-specific recurring vulnerability patterns surfaced by `threat-model.md` or `audit-report.md`. Only patterns likely to recur on future changes, NOT one-off audit findings. |

## Output Schema

One entry per candidate in `memory_candidates:` of the result envelope:

```yaml
memory_candidates:
  - type: reference                    # user | feedback | project | reference (per memory protocol)
    title: "PECL fork URL for ext-amqp"
    body: "We pin the PECL ext-amqp install to {URL} because upstream broke compatibility with PHP 8.1 in 2025-Q4. Verified working with PHP 8.1.27 + librabbitmq 0.13."
    rationale: "Surfaced from design.md DD-3 -- not obvious from Dockerfile alone, will be needed if the install ever breaks"
    surface: "external_dependencies"
```

Fields: `type` (user | feedback | project | reference), `title` (short phrase), `body` (the memory content), `rationale` (where it was surfaced from), `surface` (snake_case surface name).

## Skip Conditions

Skip the memory pass entirely ONLY if ALL of these are true:
- `state.yaml.decisions:` is empty (no mid-flight surprises).
- Verification report has 0 WARNINGS.
- Proposal `change_type` is `infra` AND every task was a pure refactor with no environment interaction.

In that case, set `memory_candidates: []` and add a note: "Memory pass skipped -- pure mechanical change, no tribal knowledge surfaced."

## Calibration

**Security surface calibration**: a one-off audit finding (e.g., "this PR's path traversal in `upload.ts:42`") is captured in the audit report and the override decision entry — those survive in the archive copy. Memory candidates from this surface should be project-level patterns the next change is likely to see again (e.g., "this codebase uses raw `${var}` interpolation in SQL across the legacy DAO layer — every change touching that layer needs explicit parameterisation review"). Err on the side of NOT capturing one-off findings.

**General calibration**: err on the side of LISTING the candidate. The orchestrator filters down. False positives are cheap (one rejection); false negatives are expensive (lost context that has to be reconstructed).
