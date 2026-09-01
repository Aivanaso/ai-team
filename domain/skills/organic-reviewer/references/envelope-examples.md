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
next_recommended:
  - "orchestrator: commit creation"
risks: []
model_used: "opus"
context_resolution: self-loaded
```

## Variant 2: review-clear, MAJOR/MINOR findings only

```yaml
status: ok
executive_summary: "Review complete for session-refresh. 2 MAJOR findings (no CRITICAL), 1 MINOR at low confidence also reported. Gate does not block; findings are informational."
group_id: session-refresh
artifacts: []
tier: 1
tier_reason: "tier 1: standard code change"
lenses:
  correctness:
    status: findings
    findings:
      - { id: "F-1", severity: MAJOR, confidence: high, evidence: read, trigger: "any request whose handler throws inside the try block at processor.ts:84 — the catch swallows it silently", file: "src/processor.ts", line: 84, claim: "Exception caught but swallowed; no log or re-throw." }
      - { id: "F-2", severity: MAJOR, confidence: medium, evidence: read, trigger: "a request that hits the error path at db.ts:112 before the connection is released", file: "src/db.ts", line: 112, claim: "Connection acquired but not released on the error path." }
      - { id: "F-3", severity: MINOR, confidence: low, evidence: read, file: "src/db.ts", line: 118, claim: "Possible off-by-one in the retry counter; could not confirm the caller's max-retry contract." }
verification:
  - { command: "<test suite>", exit_code: 0, outcome: pass }
overrides: []
verdict: review-clear
next_recommended:
  - "orchestrator: commit creation"
risks: []
model_used: "opus"
context_resolution: self-loaded
```

## Variant 3: review-blocked (≥ 1 CRITICAL)

```yaml
status: ok
executive_summary: "Review complete for cache-invalidation. 1 CRITICAL finding (confidence: low — pattern is suspicious but not conclusively provable from static reading): data race on shared mutable state. Gate is blocked (fail closed); override or re-engage required."
group_id: cache-invalidation
artifacts: []
tier: 2
tier_reason: "tier 2: modifies cross-module public contract"
lenses:
  correctness:
    status: findings
    findings:
      - { id: "F-1", severity: CRITICAL, confidence: low, evidence: read, trigger: "two concurrent requests both incrementing the shared counter at cache.ts:57 with no lock between read and write", file: "src/cache.ts", line: 57, claim: "Shared mutable counter incremented without synchronization; data race under concurrent requests." }
verification:
  - { command: "<test suite>", exit_code: 0, outcome: pass }
overrides: []
verdict: review-blocked
next_recommended:
  - "override or re-engage"
risks:
  - "CRITICAL finding F-1 requires user override or re-engage before commit"
model_used: "opus"
context_resolution: self-loaded
```

## Variant 4: review-blocked, failing blocking `review_gates` entry

```yaml
status: ok
executive_summary: "Review complete for payment-webhook. 1 CRITICAL finding: blocking review gate 'coverage' exited non-zero. Gate is blocked; override or re-engage required."
group_id: payment-webhook
artifacts: []
tier: 1
tier_reason: "tier 1: standard code change"
lenses:
  correctness:
    status: findings
    findings:
      - { id: "F-1", severity: CRITICAL, confidence: high, evidence: executed, file: ".ai-team/config.yaml", line: 34, claim: "review_gates entry 'coverage' ('<coverage check>') exited 1." }
verification:
  - { command: "<test suite>", exit_code: 0, outcome: pass }
  - { command: "<coverage check>", exit_code: 1, outcome: fail, gate: "coverage" }
overrides: []
verdict: review-blocked
next_recommended:
  - "override or re-engage"
risks:
  - "CRITICAL finding F-1 requires user override or re-engage before commit"
model_used: "opus"
context_resolution: self-loaded
```

## Variant 5: DELTA MODE, review-clear (chained via verdict_history)

```yaml
status: ok
executive_summary: "Delta pass for cache-invalidation verified F-1 closed with a mutex guard; no new inconsistency; gates re-run clean. Chain is now review-clear."
group_id: cache-invalidation
artifacts: []
tier: 2
tier_reason: "tier 2: modifies cross-module public contract"
lenses:
  correctness:
    status: pass
    findings: []
verification:
  - { command: "<test suite>", exit_code: 0, outcome: pass }
overrides: []
verdict_history:
  - { pass: full, report: ".ai-team/reviews/cache-invalidation/full.md", verdict: review-blocked, note: "1 CRITICAL: F-1 unsynchronized shared counter (src/cache.ts:57)" }
  - { pass: delta, report: ".ai-team/reviews/cache-invalidation/delta-1.md", verdict: review-clear, note: "F-1 closed with a mutex guard; no new inconsistency; gates re-run clean" }
not_reverified:
  - "concurrency lens over src/session.ts — already clean in the prior full pass, outside this delta's changed files"
verdict: review-clear
next_recommended:
  - "orchestrator: commit creation"
risks: []
model_used: "opus"
context_resolution: self-loaded
```

## Variant 6: blocked (missing context)

```yaml
status: blocked
failure_class: null             # missing-context block, not a review-step failure — see Decision Gates
executive_summary: "Required field 'group_files' is missing from injected context. Cannot determine which files to review."
group_id: null
artifacts: []
lenses: {}
verification: []
overrides: []
verdict: null                   # never review-clear/review-blocked here — no review ran, so no verdict was computed
next_recommended: []
risks:
  - "group_files: missing from injected context"
model_used: "opus"
context_resolution: fallback
```
