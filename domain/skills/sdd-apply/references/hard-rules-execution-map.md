# Hard Rules → Execution Steps Map (sdd-apply)

> Audit support for REQ-APPLY-022 and AC-08.
> Every behaviorally-prescriptive Hard Rule MUST be paired with a numbered Execution Step.

| Hard Rule # | Hard Rule text (excerpt) | Invoked by Step |
|-------------|--------------------------|-----------------|
| 1 | Follows common rules — see `_shared/common-rules.md` | Step 1 (startup) |
| 2 | Writes application source files (exception to read-only) | Step 3c |
| 3 | Write code per tasks.md exactly — no extra files | Step 3c |
| 4 | Touch only files listed in tasks | Step 3c |
| 5 | Every task leaves codebase compilable | Step 3d |
| 6 | Never modify SDD artifacts; state.yaml write limited to phases.apply.* (status, progress, commits); never author audit-trail entries | Step 3c |
| 7 | Skill-first: load project skills before writing code | Step 2 |
| 8 | Read before modifying: read file in full first | Step 3c |
| 9 | Deliverables audit before composing envelope | Step 7 |
| 10 | Group boundary hand-off: update state.yaml.progress + return control (NEVER git commit) | Step 3e |
| 11 | NEVER git commit/add/push/stash/reset/rm (only git diff --name-only permitted) | Step 7 (Step 7b self-check) |
| 12 | Do-not-invent-entities: test-orphan triggers deviation_report block + status:blocked (not audit-trail entry) | Step 3c |
| 13 | Seniority: apply implements or blocks; never authors audit-trail entries; deviation triggers deviation_report block | Step 3g |
| 14 | Evidence Protocol Rule 3: execute integration tests before status: ok. Bash available; Honesty: never status:ok without evidence | Step 3d–3e |
