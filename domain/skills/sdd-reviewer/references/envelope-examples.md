# Envelope Examples — sdd-reviewer

Standard result envelope per `_shared/result-envelope.md`, with sdd-reviewer-specific fields.

## Envelope Schema

```yaml
status: ok | blocked            # blocked only on missing context, NOT on review-blocked verdict
executive_summary: "..."
group_id: G{N}
artifacts:
  - name: review-report
    path: .ai-team/changes/{change}/review-report.md
findings: []                    # list of per-finding structures
verdict: review-clear | review-blocked
suppressed_count: 0
next_recommended: ["work-unit-commits"]   # informational; orchestrator decides per verdict
risks: []
model_used: opus
context_resolution: injected | fallback | none
```

`verdict` drives the gate:
- `review-clear` → orchestrator proceeds to invoke `work-unit-commits`
- `review-blocked` → orchestrator presents the 3-option override prompt to the user

Note: no `decisions_written` field — the reviewer is a read-only auditor; the orchestrator exclusively authors `decisions[]` override entries.

## Variant 1: review-clear, no findings

```yaml
status: ok
executive_summary: "Code-correctness review complete for G1. No findings. All four lenses clean."
group_id: G1
artifacts:
  - name: review-report
    path: .ai-team/changes/my-change/review-report.md
findings: []
verdict: review-clear
suppressed_count: 0
next_recommended:
  - "work-unit-commits"
risks: []
model_used: opus
context_resolution: injected
```

## Variant 2: review-clear, warnings only

```yaml
status: ok
executive_summary: "Code-correctness review complete for G2. 2 WARNING findings (no CRITICAL). Gate does not block; findings are informational."
group_id: G2
artifacts:
  - name: review-report
    path: .ai-team/changes/my-change/review-report.md
findings:
  - id: RV-001
    lens: error-handling
    file_line: src/processor.ts:84
    severity: WARNING
    description: "Exception caught but swallowed; no log or re-throw."
    recommendation: "Either log the exception or propagate it to the caller."
    confidence_rationale: "The catch block is empty with a comment confirming silence."
  - id: RV-002
    lens: resource-lifecycle
    file_line: src/db.ts:112
    severity: WARNING
    description: "Connection acquired but not released on the error path."
    recommendation: "Add release in finally block to ensure lifecycle closes on all paths."
    confidence_rationale: "Error path exits without entering the finally block (confirmed by reading the full function)."
verdict: review-clear
suppressed_count: 1
next_recommended:
  - "work-unit-commits"
risks: []
model_used: opus
context_resolution: injected
```

## Variant 3: review-blocked (≥ 1 CRITICAL)

```yaml
status: ok
executive_summary: "Code-correctness review complete for G3. 1 CRITICAL finding: data race on shared mutable state. Gate is blocked; override required."
group_id: G3
artifacts:
  - name: review-report
    path: .ai-team/changes/my-change/review-report.md
findings:
  - id: RV-001
    lens: concurrency
    file_line: src/cache.ts:57
    severity: CRITICAL
    description: "Shared mutable counter incremented without synchronization; data race under concurrent requests."
    recommendation: "Use an atomic operation or a lock to protect the counter update."
    confidence_rationale: "The function is called from multiple concurrent request handlers; the counter is module-level mutable state with no guard."
verdict: review-blocked
suppressed_count: 0
next_recommended:
  - "override or re-engage"
risks:
  - "CRITICAL finding RV-001 requires user override or re-engage before commit"
model_used: opus
context_resolution: injected
```

## Variant 4: blocked (missing context)

```yaml
status: blocked
executive_summary: "Required field 'group_id' is missing from injected context and not recoverable from state.yaml. Cannot determine which group to review."
group_id: null
artifacts: []
findings: []
verdict: review-clear
suppressed_count: 0
next_recommended: []
risks:
  - "group_id: missing from injected context and state.yaml"
model_used: opus
context_resolution: fallback
```
