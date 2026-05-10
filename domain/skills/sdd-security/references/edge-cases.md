# Edge Cases — sdd-security

## Edge Case 1: No security_touchpoints (threat-model mode)

**Condition:** `security_touchpoints` is an empty list in threat-model mode.

**Behavior:** Skip Steps 8.2–8.3 (touchpoint walk). STILL run Step 8.3.5 (Temporal Invariant Sweep) — the sweep is transversal and runs independently of touchpoints.

- If the temporal sweep also produces zero findings: return `status: ok`, `verdict: no-findings`, `findings: []`. Note in executive summary: "no touchpoints triggered and no temporal invariants violated — security gate clean".
- If the temporal sweep produces findings: follow normal verdict logic (WARNING → `warnings-only`, CRITICAL → `critical`).

This extends REQ-SECURITY-002 Scenario 2.2.

## Edge Case 2: All Findings Below 80% Confidence

**Condition:** Every finding generated (across all touchpoints and the temporal sweep) has confidence ≤ 80%.

**Behavior:** Suppress all findings. Return `status: ok`, `verdict: no-findings`, `findings: []`. Set `suppressed_count` to the number of suppressed findings. Note in executive summary: "All {N} candidate findings suppressed — confidence below threshold."

Rationale: false positives train reviewers to ignore findings. A clean report with a non-zero `suppressed_count` is an accurate signal that the audit ran and found only low-confidence candidates.

## Edge Case 3: Diff is Empty (code-audit mode)

**Condition:** `git diff --name-only {base_branch}..{change_branch}` returns no files.

**Behavior:** Return `status: ok`, `verdict: no-findings`, `findings: []`. Note in executive summary: "diff is empty between {base_branch} and {change_branch} — no files to audit".

Do NOT treat as an error. An empty diff is a valid state (e.g., the change was reverted, or the branch is identical to base).

## Edge Case 4: Invalid Mode Value

**Condition:** `mode` is neither `threat-model` nor `code-audit`.

**Behavior:** Return `status: blocked`. Include the invalid value in the executive summary: "Invalid mode: '{value}'. Expected threat-model or code-audit." Do not proceed with any audit steps.

## Edge Case 5: mode Missing from Injected Context

**Condition:** `mode` key is absent from the injected context block and cannot be recovered from `state.yaml`.

**Behavior:** Return `status: blocked`. Report `context_resolution: fallback` with `risks: ["mode: missing from injected context"]`. This is the one field that cannot be safely inferred — wrong mode would produce a meaningless audit.

## Edge Case 6: git Unavailable (code-audit mode)

**Condition:** `git` command is not available in the execution environment.

**Behavior:** Return `status: blocked`, message "git is not available; cannot compute diff scope for code-audit mode".

## Edge Case 7: config.yaml Missing

**Condition:** `.ai-team/config.yaml` is not found at the expected path.

**Behavior:** Return `status: blocked`, message "config.yaml not found at expected path; cannot read project configuration".

## Edge Case 8: Re-audit (Gate Fired Twice)

**Condition:** `threat-model.md` or `audit-report.md` already exists from a prior run of this mode.

**Behavior:** Overwrite the previous report. The archive phase does not need historical audit versions — the override `decisions:` entry in `state.yaml` preserves the audit trail. Do NOT return `status: blocked` because a prior report exists.

## Edge Case 9: Dependency Auditor Not Configured (code-audit)

**Condition:** `test_commands.security` is absent from `config.yaml`.

**Behavior:** Silent no-op. Log "Dependency auditor: not configured (skipped)" in the `## Dependency Auditor` section of `audit-report.md`. Do not treat as a warning or error.

## Edge Case 10: Test Infrastructure Ran but No Diff

**Condition:** The dependency auditor command ran successfully (Step 9.2) but `git diff` produced no files (diff is empty, Edge Case 3 above).

**Behavior:** This is unusual — the auditor ran but there is nothing to scan in the code. Return the auditor output in the report. Still return `verdict: no-findings` for the code categories. Note in executive summary: "dependency auditor ran; diff is empty — code categories not audited".
