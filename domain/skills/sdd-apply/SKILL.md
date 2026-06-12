---
name: sdd-apply
description: "Trigger: orchestrator launches apply after tasks approval. Implement task plan, write application source files. Commits owned by work-unit-commits. Return status: blocked with deviation_report on deviations; the orchestrator authors audit-trail entries."
disable-model-invocation: true
user-invocable: false
---

## Activation Contract

Run when the orchestrator launches the apply phase for an SDD change after tasks are approved. Produce: application source files (created, modified, removed) exactly as specified by `tasks.md`. Update `state.yaml`. Commits are exclusively owned by work-unit-commits (REQ-APPLY-021).

## Hard Rules

- Follows common rules: read-only on app code, write-scope, envelope-always, seniority — see `_shared/common-rules.md`.
- Writes application source files (exception to read-only principle — apply's primary responsibility). -- see Step 3c.
- Write code per `tasks.md` exactly. No redesign, no extra files, no bonus refactors. -- because downstream sdd-verify can only validate against the approved plan; deviation without a `deviation_report` creates undetectable scope drift. -- see Step 3c.
- Touch only files listed in tasks. If a task lists 3 files, touch exactly 3 files. -- because scope drift to unlisted files breaks the Post-Apply Audit's deliverables check (Step 7). -- see Step 3c.
- Forwarded scope guard (`allowed_edit_roots`): before writing any application-source file, verify the target path is within the injected `allowed_edit_roots` (segment-prefix per the orchestrator's Roots Computation rule). A write outside every forwarded root is a blocking deviation — return `status: blocked` with a `deviation_report` instead of writing (`kind: out-of-plan`, `out-of-roots:` evidence note). If no `allowed_edit_roots` flag is injected (or it is empty), the guard is inactive and the inner exact-file discipline governs. -- because a forwarded mechanical prefix gate is structurally harder to drift past than a buried in-scope judgment (the rationale behind the SENIORITY/TESTS_CREATED reinforcement). -- see Step 3c.
- Every task leaves the codebase compilable (or for meta-project: leaves framework files in valid Markdown structure). -- because a non-compiling intermediate state blocks all subsequent tasks in the group from executing. -- see Step 3d.
- Read SDD artifacts (`tasks.md`, `design.md`, specs, proposal) without modifying them. The only `.ai-team/` file to update is `state.yaml` (`phases.apply.*`: status, progress, commits). The orchestrator exclusively authors audit-trail entries. -- see Step 3c.
- Skill-first: read every SKILL.md path listed under `## Skills to load before work` in the delegation prompt before writing code. Skills define naming, imports, patterns, test structure; code that ignores them is wrong even if it compiles. Report `skill_resolution` in the envelope (`paths-injected` / `path-missing` / `none` — schema in `_shared/result-envelope.md`). -- because skills encode project conventions that override generic framework defaults; missing them introduces inconsistency that verification cannot catch. -- see Step 2.
- Read before modifying: always read a file in full before applying changes. -- because blind writes risk overwriting changes from earlier tasks in the same group. -- see Step 3c.
- Before composing the result envelope, verify every CREATE/MODIFY/REMOVE listed in `tasks.md` actually happened on disk. Self-reporting "X/X tasks done" without on-disk verification is a contract violation. -- see Step 7.
- Group boundary hand-off: when the last task in a group completes, update `state.yaml.phases.apply.progress[group_id] → done` and return control to the orchestrator. Leave commits to work-unit-commits (the exclusive commit owner, per REQ-APPLY-021). -- see Step 3e.
- Use only read-only git commands (`git diff --name-only` or `git status --porcelain`) during the deliverables audit. State-changing git commands (commit, add, push, stash, reset, rm) are exclusively owned by work-unit-commits. -- see Step 7. Grep contract enforced by verify.
- Respect entity boundaries (test-orphan): if a test references a symbol, file, route, command, or interface not in the system under test, the FIRST hypothesis is test-orphan (wrong contract). Classify as `test-with-AC-trace` (justified by a REQ in tasks.md) or `test-orphan` (no REQ anchor). For test-orphan: return `status: blocked` with `deviation_report.kind: test-orphan`. The orchestrator decides whether to add the entity per REQ or to re-engage sdd-tasks. -- see Step 3g-replacement.
- Seniority: apply implements or blocks. Per Seniority Model (REQ-CR-008 in `_shared/common-rules.md`): detect any deviation trigger (out-of-plan, design-pivot, test-orphan, new runtime dependency), compose the `deviation_report` block (schema in `_shared/result-envelope.md`), return `status: blocked`. Surface the deviation via the `deviation_report` block in the envelope (the orchestrator translates this into a `decisions[]` entry). -- see Step 3g.
- Evidence Protocol Rule 3: if a task generates integration tests, execute them before marking `status: ok`. (Meta-project: Manual Review Checklist criteria substitute.) -- see Step 3d–3e.
- Bash is available — see `_shared/sdd-orchestrator-protocol.md` "Tool Availability by Phase: apply". Honesty: the envelope MUST include `execution_evidence` populated with the literal stdout of every verify command declared in `config.yaml` (typecheck, lint) and of each test file created during this phase. An absent or empty `execution_evidence` is a contract violation. If a verify command cannot be run (Bash denied, missing dependency), set `status: blocked` listing the exact command and reason. -- see Step 7.

## Decision Gates

| Condition | Action |
|---|---|
| Task already `done` in `state.yaml` | Skip (verify output files still exist; re-implement if missing). |
| Task not in `scope` list | Skip. |
| Dependency is `failed` or `pending` | Check independence. If dependent, mark `skipped`; if independent, proceed. |
| Compilation fails after 2 attempts | Mark task `failed`; continue to next independent task. |
| Integration tests generated by this task | Execute them before `status: ok` per Rule 14 (Evidence Protocol Rule 3). |
| Out-of-plan fix required | Return `status: blocked` with `deviation_report.kind: out-of-plan`. Orchestrator decides: approve drift (authors audit-trail entry, re-engages apply with refined scope), or escalate to user. |
| Test entity has no REQ anchor in tasks.md | Return `status: blocked` with `deviation_report.kind: test-orphan` — failed test inlined, missing-entity grep result attached. Orchestrator routes to sdd-tasks (test contract owner). |
| `strict_tdd: true` in injected context | Follow strict-tdd module: red → green → triangulate → refactor. |
| `phases.apply.status` already `done` | Return immediately. Nothing to do. |
| Tests created by tasks in the current group are red at group boundary | Mark the test-creating task(s) `partial` (not `done`) in `state.yaml`. Set envelope `status: warning`. Record the test stdout in `execution_evidence.tests_created[]`. |
| Target application-source path falls outside the forwarded `allowed_edit_roots` | Leave the file unwritten. Return `status: blocked` with `deviation_report.kind: out-of-plan`, `evidence.file` = attempted path, `evidence.output` = `out-of-roots: target '<path>' not within allowed_edit_roots [...]`, `suggested_action: re-engage-apply-refined`. Halts further task execution (subsequent tasks skipped, same as the existing out-of-plan block). If no `allowed_edit_roots` injected/empty → guard inactive, proceed under inner exact-file discipline. |

## Execution Steps

1. Read `_shared/context-protocol.md` (startup), `_shared/persistence-contract.md` (write rules). Validate injected context; recover missing fields from `state.yaml`, report `context_resolution: fallback` if needed.
2. Read `config.yaml`: stack, architecture, verify commands. Read in full every SKILL.md path under `## Skills to load before work` from the delegation prompt (project stack conventions — e.g. backend framework, frontend framework, language strictness, test runner). When the prompt carries no skills block, proceed on `config.yaml` conventions and report `skill_resolution: none`; when a listed path is absent on disk, continue without it and report `skill_resolution: path-missing` with the path in `risks`.
3. Read `tasks.md` in full. Parse Execution Order table → ordered task list with IDs, files, dependencies, implementation notes. Read `state.yaml` to find already-completed tasks.
4. Pre-flight structural scan (does NOT count as implementation): glob to verify MODIFY targets exist, CREATE targets do not exist, REMOVE targets exist. Assess drift per [references/task-execution-loop.md](references/task-execution-loop.md).
5. For each task in Execution Order, run the per-task loop per [references/task-execution-loop.md](references/task-execution-loop.md):

   **3a — Gate check** (skip/dependency logic).

   **3b — Set task `active`** in `state.yaml` before touching any file.

   **3c — Implement files** in dependency order (types → entities → DTOs → services → controllers → modules → pages). For new test entities: classify as `test-with-AC-trace` (REQ in tasks.md justifies it) or `test-orphan` (no REQ anchor — do NOT add, return `status: blocked` with `deviation_report.kind: test-orphan` per Step 3g). See [references/task-execution-loop.md](references/task-execution-loop.md) for CREATE / MODIFY / REMOVE per-action prose.

   **Pre-write roots guard (REQ-APPLY-024).** If an `allowed_edit_roots` flag was injected and
   is non-empty: before each application-source CREATE/MODIFY/REMOVE write, evaluate whether the
   target path is within the forwarded roots, using the within-roots formula from the
   orchestrator's Roots Computation rule (normalize: strip leading `./`, strip trailing `/`;
   target `T` is within root `R` iff `T == R` OR `T` begins with `R + "/"`; partial-name
   siblings like `src/foobar` under `src/foo` stay outside the root). A target containing any
   `..` segment, or an absolute path (leading `/`), is outside all roots by definition — reject
   without prefix comparison (never resolve `..`; `root/../../x` blocks). The check runs for **every**
   application-source write, not only suspicious ones.
   - **Within roots:** proceed with the write normally.
   - **Outside all roots:** leave the file unwritten and immediately compose a `deviation_report`
     (`kind: out-of-plan`; `task_ref` = current task; `evidence.file` = attempted target path;
     `evidence.output` = `out-of-roots: target '<attempted-path>' not within
     allowed_edit_roots [<root>, <root>, ...]`; `suggested_action: re-engage-apply-refined`) and
     return `status: blocked`. This is the same block-and-escalate path as the existing
     out-of-plan deviation (Step 3g) — populate `tasks_status.skipped` with all not-yet-attempted
     tasks; stop.
   - **No flag injected / empty flag (REQ-APPLY-025):** the guard is inactive. Proceed using only
     the inner exact-file discipline (touch exactly the files declared in `tasks.md`); no blocking
     occurs on account of an absent roots flag; behavior matches the pre-guard baseline.

   **3d — Verify compilation** using `config.yaml` verify commands. Fix up to 2 attempts. Mark `done` or `failed`.

   **3e — Group boundary detection and hand-off:** when the last task in a group completes:
   1. (3e.1) Run the test files created by tasks in this group using the test runner from `config.yaml`. Capture command, exit code, passed/failed counts into `execution_evidence.tests_created[]`. If any test file has `exit_code != 0` OR `failed > 0`: mark the corresponding task(s) `partial` (NOT `done`) — sdd-verify is the authoritative judge of full-suite compliance. Mark the task `partial` (not `done`) while the tests it created are red.
   2. (3e.2) Update `state.yaml`: set `phases.apply.progress[{group_id}] = done`. The group_id is the literal string "G1", "G2", etc. from the Execution Order table.
   3. (3e.3) Return control to the orchestrator; it will invoke `work-unit-commits` per REQ-ORCHESTRATOR-010. State-changing git commands are outside apply's scope.

   **3f — Update progress** in `state.yaml` (`done` / `failed` / `skipped`).

   **3g — On any deviation: compose deviation_report and block (MANDATORY):**

   When any of these triggers fire, compose a `deviation_report` block and return
   `status: blocked` immediately. Compose and return the `deviation_report` block in the envelope; stop task execution.

   Triggers:
   - About to write a fix not in any task in `tasks.md` (out-of-plan).
   - A new REQUIRED value (column, env var, constructor param, header) forces edits to fixtures/mocks/factories that `tasks.md` does not declare (out-of-plan fanout). Mechanical-and-obvious still routes through the deviation_report — the orchestrator approves scoped mechanical fanout in minutes, and the declaration keeps the audit trail whole.
   - Discovered a design.md assumption that does not hold in the actual codebase (design-pivot).
   - Added a runtime dependency, config flag, or infra piece not in the original task plan.
   - Test references a symbol/file/route/command/interface absent from the system (test-orphan).

   For each trigger, set `deviation_report.kind` to the matching value:
   `out-of-plan | design-pivot | test-orphan`

   Schema — per `_shared/result-envelope.md`:

   ```yaml
   deviation_report:
     kind: out-of-plan | design-pivot | test-orphan
     task_ref: "{task-id from tasks.md}"
     evidence:
       file: "{path or null}"
       line: {int or null}
       command: "{verbatim command or null}"
       output: "{last-15-lines or null}"
     suggested_action: "re-engage-tasks | re-engage-design | re-engage-apply-refined | escalate-user"
   ```

   Return `status: blocked`. Populate `tasks_status.skipped` with all tasks not yet attempted.
   Stop at the first deviation trigger and return `status: blocked`.

   **Cost gate:** trivial typos, lint fixes, or whitespace corrections within a single task
   do NOT trigger a block — handle inline without an envelope change.

6. After all tasks: update `state.yaml` — `phases.apply.status → done`, `phases.apply.completed → ISO 8601`, `phases.apply.agent → sdd-apply`, `current_phase → apply`, `updated → now`. If some tasks failed, status is still `done`; record `failed` and `skipped` in `progress`.
7. **Deliverables audit (mandatory, before composing the envelope).**

   For each task in `tasks.md` with a `Files:` block:
   - Each CREATE path MUST exist on disk. Verify with `find {project_root}/{path}` or `ls`.
   - Each MODIFY path MUST appear in `git diff HEAD --name-only` (or have an uncommitted change in the working tree if commits are deferred).
   - Each REMOVE path MUST be gone.

   Build a `tasks_status` map: `{ completed: [...ids], partial: [...ids], skipped: [...ids] }`. A task is `partial` if any of its declared deliverables is missing.

   If any task is `partial` or `skipped`:
   - Set envelope `status: warning` (NOT `ok`).
   - Surface each missing deliverable in `risks:` with task ID + path.
   - Report `completed/partial/skipped` counts truthfully in `executive_summary`.

   **7b — Self-check (informational):** Run: `grep -E 'git (commit|add|push|stash|reset|rm)' domain/skills/sdd-apply/SKILL.md`. Expect 0 matches (git state-changing commands must not appear in apply's own SKILL.md as instructions). Record output in envelope if non-zero.

   **Critical guard (meta-project):** The 4 extra SKILL.md files from R-12 (sdd-propose, sdd-spec, sdd-design, sdd-security) MUST each contain the consolidated inherit line at the end of Hard Rules. Absence is a CRITICAL gap for AC-07.

   The verify phase has its own audit, but the apply envelope MUST be the first line of defense — the orchestrator should not need to discover skips during verify.

   **7c — Execution evidence audit (mandatory before composing the envelope):**
   - Read `config.yaml` verify commands list (typecheck, lint, test).
   - Confirm `execution_evidence.typecheck.exit_code == 0` (if config declares a typecheck command). Non-zero → envelope `status: warning`.
   - Confirm `execution_evidence.lint.exit_code == 0` (if config declares a lint command). Non-zero → envelope `status: warning`.
   - Confirm every entry in `execution_evidence.tests_created[]` has `exit_code == 0` AND `failed == 0`. Any failure → the corresponding task(s) are `partial` (not `done`), envelope `status: warning`.
   - If a verify command could not run at all (Bash denied, missing tool) → return `status: blocked` in this case — `status: ok` without execution evidence corrupts the apply audit trail.
   - Record each check result (pass / fail / skipped-no-config) in `executive_summary`.

8. Return the envelope per [references/envelope-examples.md](references/envelope-examples.md).

## Output Contract

Write application source files per `tasks.md`. Update `state.yaml` (`phases.apply.status → done`, `phases.apply.completed → ISO 8601`, `phases.apply.agent → sdd-apply`, `current_phase → apply`, `updated → now`). Return a result envelope with `status`, `executive_summary` (truthful completed/partial/skipped counts per Step 7), `artifacts`, `tasks_status`, `execution_evidence` (REQUIRED — populated stdout of all verify commands + created test files), `next_recommended`, `risks` (populated when any deliverable is missing), `model_used`, `context_resolution`, `skill_resolution` (REQUIRED — `paths-injected` / `path-missing` / `none` per Step 2), `deviation_report` (REQUIRED when `status: blocked` on any structured deviation — schema in `_shared/result-envelope.md`; ABSENT on `status: ok` or `status: warning`).

## References

- [references/task-execution-loop.md](references/task-execution-loop.md) — Step 3a-3f detailed prose, gate check rules, implementation order, CREATE/MODIFY/REMOVE per-action prose, compilation flow, drift detection; load at Step 5.
- [references/hard-rules-execution-map.md](references/hard-rules-execution-map.md) — mapping of each Hard Rule to its Execution Step; audit support for REQ-APPLY-022 and AC-08; load when verify requests orphan-rule audit.
- [references/block-and-re-engage-examples.md](references/block-and-re-engage-examples.md) — worked deviation_report blocks (out-of-plan, design-pivot, test-orphan); load when composing a `deviation_report` block in a blocked envelope.
- [references/envelope-examples.md](references/envelope-examples.md) — all-succeeded, with-warnings, blocked envelope variants; load at Step 8.
- [references/edge-cases.md](references/edge-cases.md) — Resumed Execution, Compilation Failure, File Already Exists, Missing File for MODIFY, Circular Dependency, No Verify Commands, Scope Limiting; load when an unexpected condition arises.
- `../_shared/context-protocol.md` — startup sequence; load first.
- `../_shared/persistence-contract.md` — write rules, audit-trail schema; load at Step 1.
- `../_shared/common-rules.md` — consolidated principles (read-only, write-scope, envelope-always, seniority); load at startup.
- `../_shared/result-envelope.md` — envelope schema; load at Step 8.
- `../_shared/evidence-protocol.md` — Rules 1-6 (Rule 3 governs integration test execution before status:ok; Rule 6 governs orchestrator post-apply audit).
