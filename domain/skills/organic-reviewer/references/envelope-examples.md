# Envelope Examples — organic-reviewer

Standard result envelope per `_shared/result-envelope.md`, with organic-reviewer's Review
Receipt fields flattened in (see `_shared/result-envelope.md` → Review Receipt for the
canonical schema).

## Variant 1: review-clear, no findings

```yaml
status: ok
executive_summary: "Correctness + verification review complete for billing-export. No findings across all five lenses. Both acceptance checks re-ran clean."
group_id: billing-export
artifacts: []
tier: 1
tier_reason: "tier 1: standard code change"
lenses:
  correctness:
    status: pass
    findings: []
verification:
  - { command: "<lint check>", exit_code: 0, outcome: pass }
  - { command: "<smoke check>", exit_code: 0, outcome: pass }
overrides: []
verdict: review-clear
suppressed_count: 0
next_recommended:
  - "work-unit-commits"
risks: []
model_used: "opus"
context_resolution: self-loaded
```

## Variant 2: review-clear, MAJOR/MINOR findings only

```yaml
status: ok
executive_summary: "Review complete for session-refresh. 2 MAJOR findings (no CRITICAL). Gate does not block; findings are informational."
group_id: session-refresh
artifacts: []
tier: 1
tier_reason: "tier 1: standard code change"
lenses:
  correctness:
    status: findings
    findings:
      - { id: "F-1", severity: MAJOR, file: "src/processor.ts", line: 84, claim: "Exception caught but swallowed; no log or re-throw." }
      - { id: "F-2", severity: MAJOR, file: "src/db.ts", line: 112, claim: "Connection acquired but not released on the error path." }
verification:
  - { command: "<test suite>", exit_code: 0, outcome: pass }
overrides: []
verdict: review-clear
suppressed_count: 1
next_recommended:
  - "work-unit-commits"
risks: []
model_used: "opus"
context_resolution: self-loaded
```

## Variant 3: review-blocked (≥ 1 CRITICAL)

```yaml
status: ok
executive_summary: "Review complete for cache-invalidation. 1 CRITICAL finding: data race on shared mutable state. Gate is blocked; override or re-engage required."
group_id: cache-invalidation
artifacts: []
tier: 2
tier_reason: "tier 2: modifies cross-module public contract"
lenses:
  correctness:
    status: findings
    findings:
      - { id: "F-1", severity: CRITICAL, file: "src/cache.ts", line: 57, claim: "Shared mutable counter incremented without synchronization; data race under concurrent requests." }
verification:
  - { command: "<test suite>", exit_code: 0, outcome: pass }
overrides: []
verdict: review-blocked
suppressed_count: 0
next_recommended:
  - "override or re-engage"
risks:
  - "CRITICAL finding F-1 requires user override or re-engage before commit"
model_used: "opus"
context_resolution: self-loaded
```

## Variant 4: blocked (missing context)

```yaml
status: blocked
executive_summary: "Required field 'group_files' is missing from injected context. Cannot determine which files to review."
group_id: null
artifacts: []
lenses: {}
verification: []
overrides: []
verdict: review-clear
suppressed_count: 0
next_recommended: []
risks:
  - "group_files: missing from injected context"
model_used: "opus"
context_resolution: fallback
```
