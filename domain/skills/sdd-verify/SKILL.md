---
name: sdd-verify
description: "Trigger: orchestrator launches verify after apply (and code-audit gate). Validate change against ACs, run tests, produce verification report."
disable-model-invocation: true
user-invocable: false
---

## Activation Contract

Run when the orchestrator launches the verify phase for an SDD change after apply completes. Produce: `verification-report.md` and `state.yaml` update. Never modify application code, specs, design, or any SDD artifact other than `state.yaml`.

## Hard Rules

- Read-only on application code. Not a single character changed, not even to fix a bug.
- Write only `verification-report.md` (plus `state.yaml` update).
- Verify against specs, not opinion. If the code does what the spec says, it passes.
- Evidence required. Every verdict needs a command output, file:line reference, or test name:result. "Looks correct" is not evidence.
- Run real commands. Compile, lint, test. Do not guess whether the build passes.
- Tests are behavioral proof. A spec scenario is only COMPLIANT when a test that covers it has PASSED. Code existing in the codebase is structural evidence (Step 6), not behavioral proof (Step 8).
- Bash is available — see "Tool Availability by Phase: verify" in `_shared/sdd-orchestrator-protocol.md`. Step 5 (test execution) is non-skippable: if unable to execute, return `status: needs_input` listing the required commands — never declare COMPLIANT without test execution evidence.

## Decision Gates

| Condition | Action |
|---|---|
| `phases.apply.status` is not `done` | Return `status: blocked` immediately. |
| CRITICAL finding (broken build, failing test, MUST req missing) | Block archive. List in Issues/CRITICAL. Overall verdict: FAIL. |
| WARNING finding (SHOULD gap, scope creep, design deviation) | Flag and continue. Overall verdict: PASS WITH WARNINGS. |
| SUGGESTION only | Record. No gate action. Verdict not downgraded. |
| Failure in `baseline.md` | Not a regression -- pre-existing. Do not report as CRITICAL. |
| Design drift that has a `state.yaml.decisions:` entry with `task_ref` | Approved drift. Carry verbatim into Drift Summary table. Not scope creep. |
| Missing test infrastructure (no runner, no tests) | Downgrade all UNTESTED from CRITICAL to WARNING. Status: warning with manual check note. |
| `baseline_path` not injected but `baseline.md` exists on disk | Recover from disk. Report `context_resolution: fallback`. |

## Execution Steps

1. Read `_shared/context-protocol.md` (startup), `_shared/persistence-contract.md` (write rules). Validate injected context. Recover missing fields from `state.yaml`; report `context_resolution: fallback` if any were missing.
2. Load: `config.yaml` (stack, verify commands), `state.yaml` (`phases.apply.status`, apply progress), `tasks.md` (full), delta specs (all domains), `proposal.md` (ACs), `design.md`. If `baseline.md` exists, read it -- failures present there are pre-existing, not regressions.
3. File inventory: for each task/file pair verify CREATE exists, MODIFY exists-and-changed, REMOVE is gone. Run `git diff --name-only HEAD`; files in diff but not in any task = scope creep WARNING.
4. Build: run compile command from `config.yaml`. Compilation error = CRITICAL. Run lint on created/modified files; lint error = CRITICAL, lint warning = WARNING.
5. Test execution: run new test files created by tasks (CRITICAL if failing). Run regression suite for affected modules (CRITICAL if regressions). No test runner configured = WARNING, not CRITICAL.
6. Task criteria: for each task verify each checklist item. Unmet critical criteria = CRITICAL; unmet optional criteria = WARNING.
7. Static correctness: for each delta-spec requirement, read implementing files (use tasks.md traceability). Assess Given/When/Then structurally. Verdict per requirement: Implemented / Partial / Missing. MUST gaps = CRITICAL; SHOULD gaps = WARNING.
8. Design coherence: for each key design decision verify the approach was followed. Deviation = WARNING (design is a guide, not law).
9. Behavioral compliance: cross-reference every spec scenario against Step 5 test results. COMPLIANT = test exists AND passed. FAILING = test failed = CRITICAL. UNTESTED MUST = CRITICAL (WARNING if no test infra). UNTESTED SHOULD = WARNING.
10. **Step 8b -- Drift Summary:** Read `state.yaml.decisions:` (schema in `_shared/persistence-contract.md`). For each entry with `phase` and `task_ref`, write one row in the Drift Summary table (Phase / Task ref / Decision / Reason / Evidence / Commits) -- these are approved drift, not scope creep. Security-override entries (`task_ref: "security-override"`) reference finding IDs in the audit artifact -- carry verbatim. Unaccounted drift (diff files not in tasks.md and not in any `decisions:` entry) = WARNING.
11. AC coverage: for each AC, combine static (Step 7) and behavioral (Step 9) verdicts. COVERED = all traced reqs Implemented + Compliant. PARTIAL = some gaps. NOT COVERED = missing or failing. Report in `| AC | Status | Evidence |` table.
12. Overall verdict: FAIL if any CRITICAL. PASS WITH WARNINGS if warnings only. PASS if zero findings.
13. Write `verification-report.md` per [references/report-format.md](references/report-format.md).
14. Update `state.yaml`: `phases.verify.status → done`, `phases.verify.completed → ISO 8601`, `phases.verify.agent → sdd-verify`, `current_phase → verify`, `updated → now`. Return envelope per [references/envelope-examples.md](references/envelope-examples.md).

## Output Contract

Write `.ai-team/changes/{change}/verification-report.md`. Update `state.yaml` (`phases.verify.status → done`, `completed`, `agent`, `current_phase → verify`, `updated`). Return a result envelope with `status`, `executive_summary`, `artifacts`, `next_recommended`, `risks` (if any), `model_used`, `context_resolution`.

## References

- [references/report-format.md](references/report-format.md) — full verification-report template (Summary table, AC Coverage, Static Correctness, Behavioral Compliance, Drift Summary, Issues, Verdict); load at Step 13.
- [references/envelope-examples.md](references/envelope-examples.md) — PASS, PASS WITH WARNINGS, FAIL, Blocked envelope variants; load at Step 14.
- [references/edge-cases.md](references/edge-cases.md) — Apply Partially Failed, No Tests, No Delta Specs, Large Codebase, Compilation Passes But Code Wrong, Resumed Verification, Verify Commands Missing, Design Missing; load when an unexpected condition arises.
- `../_shared/context-protocol.md` — startup sequence; load first.
- `../_shared/persistence-contract.md` — write rules, `decisions:` schema; load at Step 1.
- `../_shared/result-envelope.md` — envelope schema; load at Step 14.
- `../_shared/evidence-protocol.md` — Rules 1-5 (Rule 3 governs real-command execution).
- `../_shared/spec-convention.md` — REQ-ID format, RFC 2119 keywords; load at Step 7.
