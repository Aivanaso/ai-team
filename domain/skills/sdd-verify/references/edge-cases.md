# Edge Cases — sdd-verify

> Handling for non-happy-path situations. Load when an unexpected condition arises.

## Apply Partially Failed

If `state.yaml` shows some tasks as `failed` or `skipped` in apply progress:

1. Verify only the tasks marked `done` -- skip failed/skipped tasks.
2. Note skipped tasks in the report: "Tasks {IDs} were not applied (status: {failed/skipped}) -- excluded from verification."
3. For spec compliance: requirements that depend only on failed tasks get verdict SKIP, not CRITICAL.
4. Overall verdict: max PASS WITH WARNINGS (cannot be clean PASS if tasks were skipped).

## No Tests in Project

If the project has no test runner and tasks created no test files:

- Steps 4a and 4b: SKIP.
- Step 8 (Behavioral Compliance): all scenarios get UNTESTED, downgraded from CRITICAL to WARNING.
- Note: "No test infrastructure -- behavioral compliance based on static analysis only (Step 6). Manual testing required before archive."
- Static correctness (Step 6) becomes the primary compliance evidence.

## No Delta Specs

If specs were skipped (proposal went straight to design):

- Steps 6 and 8: trace against proposal ACs directly instead of requirements.
- Note: "Spec compliance traced to ACs -- delta specs not available."
- Step 9 becomes redundant (same data source) -- merge into Steps 6/8.

## Large Codebase (50+ Changed Files)

Budget your reads. Do NOT read every file.

| Priority | Read | Why |
|----------|------|-----|
| 1 | Files from FAIL tasks in apply | Most likely to have issues |
| 2 | Files implementing MUST requirements | Critical path |
| 3 | Complex files (services, business logic) | Higher defect probability |
| 4 | Simple files (DTOs, types, modules) | Spot-check a sample |

For 50+ files, read 20-30 max. Spot-check simple files rather than reading all of them. Note in report: "Spot-checked {N}/{total} files for static correctness."

## Compilation Passes But Code Is Wrong

Compiling does not mean correct. A service that returns an empty array instead of querying the database will compile fine.

- Compilation (Step 3) and behavioral compliance (Step 8) are independent checks.
- Code that compiles but doesn't implement the spec scenario: PASS for build, CRITICAL for compliance.
- The overall verdict reflects both.

## Resumed Verification

If `state.yaml` shows `phases.verify.status: active` (interrupted mid-verify):

- Check if `verification-report.md` exists (partial report from prior run).
- If exists: read it, identify which steps completed, resume from the next step.
- If not: start from Step 1.

## Verify Commands Missing From Config

If config.yaml has no `verify` section:

- Try to auto-detect from package.json scripts: `build`, `typecheck`, `lint`, `test`.
- If nothing found: compile and lint steps become SKIP with status: warning.
- Note limitation: "No verify commands configured -- build verification skipped."

## Design Document Missing

If design.md does not exist (was skipped):

- Step 7 (Design Coherence): SKIP entirely.
- Note: "Design coherence skipped -- no design.md available."
- This does NOT affect other steps.
