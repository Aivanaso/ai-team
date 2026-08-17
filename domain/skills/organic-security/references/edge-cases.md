# Edge Cases — organic-security

## Edge Case 1: No security_touchpoints (threat-model mode)

**Condition:** `security_touchpoints` is absent or empty in threat-model mode.

**Behavior:** Infer touchpoints from `scope_description` text via the nine-slug heuristics.
STILL run the Temporal Invariant Sweep and the Seam & Failure Sweep — both are transversal
and run independently of touchpoints.

- If both sweeps also produce zero findings: return `status: ok`, `security_lens.status: pass`,
  `findings: []`. Note in executive summary: "no touchpoints triggered and no temporal
  invariants violated — security lens clean".
- If either sweep produces findings: follow normal severity logic (≥1 CRITICAL → `warning`
  base status; MAJOR/MINOR only → `ok` base status with `security_lens.status: findings`).

## Edge Case 2: All Findings Below 80% Confidence

**Condition:** Every finding generated (across all touchpoints and both sweeps) has
confidence ≤ 80%.

**Behavior:** Suppress all findings. Return `status: ok`, `security_lens.status: pass`,
`findings: []`. Set `suppressed_count` to the number of suppressed findings. Note: "All {N}
candidate findings suppressed — confidence below threshold."

Rationale: false positives train reviewers to ignore findings. A clean report with a non-zero
`suppressed_count` is an accurate signal that the audit ran and found only low-confidence
candidates.

## Edge Case 3: group_files Empty or None Exist (code-audit mode)

**Condition:** The injected `group_files` list is empty, or none of the declared paths exist
on disk under `project_root`.

**Behavior:** Return `status: ok`, `security_lens.status: pass`, `findings: []`. Note in
executive summary: "group_files is empty or unresolvable under project_root — no files to
audit".

## Edge Case 4: Invalid Mode Value

**Condition:** `mode` is neither `threat-model` nor `code-audit`.

**Behavior:** Return `status: blocked` with the invalid value in the executive summary:
"Invalid mode: '{value}'. Expected threat-model or code-audit." Wait for the orchestrator to
correct the mode before proceeding.

## Edge Case 5: mode Missing from Injected Context

**Condition:** `mode` key is absent from the injected context block.

**Behavior:** Return `status: blocked`. Report `context_resolution: fallback` with
`risks: ["mode: missing from injected context"]`. `mode` is the one field that requires
explicit injection — an inferred mode would produce a meaningless audit.

## Edge Case 6: git Unavailable (code-audit mode)

**Condition:** `git` command is not available in the execution environment.

**Behavior:** Continue the file-set audit without git scope inspection (`group_files` is
already an explicit list, not a diff) — git is only used for auxiliary status checks, never
to compute scope on this route. Note the limitation in `risks` if a git-based check (e.g.
dependency auditor invoking git) fails.

## Edge Case 7: config.yaml Missing

**Condition:** `.ai-team/config.yaml` is not found at `project_root`.

**Behavior:** Continue the audit; log "Dependency auditor: not configured (skipped)" in the
`## Dependency Auditor` section and note in `risks`: "config.yaml not found — dependency
auditor step skipped."

## Edge Case 8: Re-audit (Gate Fired Twice)

**Condition:** The file at `report_destination` already exists from a prior run of this mode.

**Behavior:** Overwrite the previous report. The envelope's `security_lens` for this run is
the current record; no history is preserved by this skill.

## Edge Case 9: Dependency Auditor Not Configured (code-audit)

**Condition:** `test_commands.security` is absent from `config.yaml`.

**Behavior:** Log "Dependency auditor: not configured (skipped)" in the `## Dependency
Auditor` section of `audit-report.md`. Continue normally.

## Edge Case 10: Test Infrastructure Ran but group_files Is Empty

**Condition:** The dependency auditor command ran successfully but `group_files` resolved to
zero files (Edge Case 3 above).

**Behavior:** This is unusual — the auditor ran but there is nothing to scan in the code.
Return the auditor output in the report. Still return `security_lens.status: pass` for the
code categories. Note in executive summary: "dependency auditor ran; group_files is empty —
code categories not audited".
