# Envelope Examples — sdd-verify

> Load at final step when building the result envelope.

## All Checks Pass

```yaml
status: ok
executive_summary: "Verification passed for {change-name}. {N} files verified, build clean, {test-count} tests pass, {scenario-count}/{total} scenarios behaviorally compliant. Ready for archive."
citations_unresolved: 0
artifacts:
  - name: "verification-report"
    path: ".ai-team/changes/{change-name}/verification-report.md"
  - name: "state"
    path: ".ai-team/changes/{change-name}/state.yaml"
next_recommended:
  - "archive"
model_used: "{resolved-model}"
context_resolution: "injected"
```

## Pass With Warnings

```yaml
status: warning
executive_summary: "Verification completed for {change-name} with {N} warnings. {summary of warnings}. No critical failures."
citations_unresolved: 0
artifacts:
  - name: "verification-report"
    path: ".ai-team/changes/{change-name}/verification-report.md"
  - name: "state"
    path: ".ai-team/changes/{change-name}/state.yaml"
next_recommended:
  - "archive"
risks:
  - "{warning 1}"
  - "{warning 2}"
model_used: "{resolved-model}"
context_resolution: "injected"
```

## Verification Failed

```yaml
status: failed
executive_summary: "Verification failed for {change-name}. {N} critical issues: {brief list}. See verification report for details."
citations_unresolved: {N from Step 15b — non-zero only here: rows the agent could not honestly downgrade}
artifacts:
  - name: "verification-report"
    path: ".ai-team/changes/{change-name}/verification-report.md"
  - name: "state"
    path: ".ai-team/changes/{change-name}/state.yaml"
next_recommended:
  - "apply"
risks:
  - "{failure 1 -- which tasks need re-apply}"
  - "{failure 2}"
model_used: "{resolved-model}"
context_resolution: "injected"
```

## Blocked

```yaml
status: blocked
executive_summary: "Cannot verify -- {reason}."
artifacts: []
next_recommended:
  - "{what needs to happen first}"
risks:
  - "{blocker details}"
model_used: "{resolved-model}"
context_resolution: "injected"
```
