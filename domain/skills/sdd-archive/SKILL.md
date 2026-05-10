---
name: sdd-archive
description: "Trigger: orchestrator launches archive after verify passes. Merge delta specs, copy to archive, surface memory candidates."
disable-model-invocation: true
user-invocable: false
---

## Activation Contract

Run when the orchestrator launches the archive phase for an SDD change whose verify status is `done`. Produce: merged base specs, archived change directory, memory candidates list. Never run if verify is not `done`.

## Hard Rules

- Touch only `.ai-team/` files; never application code.
- Run only after verify reports `done` with verdict PASS or PASS WITH WARNINGS; otherwise return `status: blocked`.
- Apply the merge algorithm exactly: ADDED appends, MODIFIED replaces, REMOVED deletes. No creative interpretation.
- Copy to archive BEFORE deleting the active change directory. If copy fails, abort.
- Always include `memory_candidates:` in the envelope (possibly empty). The orchestrator depends on this field.
- `memory_candidates:` MUST be populated BEFORE any destructive step (`cp -r`, `rm -rf`). If destructive steps fail (e.g., Bash denied), return `status: warning` with the populated `memory_candidates:` — never return without them. Memory is the only output that cannot be reconstructed from disk; specs/copies are recoverable by re-running the failed step.
- Bash is available — see "Tool Availability by Phase: archive" in `_shared/sdd-orchestrator-protocol.md`. Run `cp -r` and `rm -rf` per Steps freely; the `memory_candidates`-first rule above remains the safety net for any failure.

## Decision Gates

| Condition | Action |
|---|---|
| `phases.verify.status` not `done` | Return `status: blocked`. |
| Verify verdict is FAIL | Return `status: blocked` with reason "verify failed -- resolve issues first". |
| `state.yaml.decisions:` empty AND verification has 0 warnings AND `change_type: infra` AND every task pure refactor | Skip Step 1 memory pass; return `memory_candidates: []` with skip note. |
| Base spec missing for a delta domain | Treat the delta as the new base spec; strip ADDED/MODIFIED/REMOVED headers. |
| MODIFIED REQ-ID not found in base | Treat as ADDED; record note. |
| Archive name collides with existing directory | Append `-2`, `-3`, … counter. |

## Execution Steps

1. Run the memory capture pass per [references/memory-capture.md](references/memory-capture.md). Surface candidates from proposal, design, tasks, verification-report, and `state.yaml.decisions:`.
2. Read `state.yaml`; verify the gate per Decision Gates above.
3. **Compose envelope draft** with `memory_candidates:` populated from Step 1, `status` undecided yet, `artifacts:` empty. Hold it in memory; do not emit yet. This guarantees that if any subsequent destructive step fails, the orchestrator still receives the memory list.
4. For each delta spec under `.ai-team/changes/{change-name}/specs/{domain}/spec.md`, apply ADDED / MODIFIED / REMOVED to `.ai-team/specs/{domain}/spec.md` per `_shared/spec-convention.md`. If `skip_spec: true`, skip this step.
5. Copy `.ai-team/changes/{change-name}/` to `.ai-team/changes/archive/YYYY-MM-DD-{change-name}/` using ISO 8601 date.
6. Delete the active change directory.
7. **Emit final envelope** per [references/envelope-examples.md](references/envelope-examples.md). If steps 4-6 succeeded → `status: ok` with completed paths in `artifacts:`. If any of 4-6 failed (Bash denied, copy collision, etc.) → `status: warning` with the same `memory_candidates:` from Step 3, completed steps listed in `artifacts:`, and failed steps listed in `risks:` with the exact failure (e.g., "Bash denied for `cp -r`; orchestrator must complete copy and delete inline").

## Output Contract

Write `.ai-team/changes/archive/YYYY-MM-DD-{change-name}/` (full copy of artifacts). Update `.ai-team/specs/{domain}/spec.md` for each merged delta. Delete `.ai-team/changes/{change-name}/`. Return envelope with `status`, `executive_summary`, `artifacts`, `next_recommended: []`, `memory_candidates`, `model_used`, `context_resolution`.

## References

- [references/memory-capture.md](references/memory-capture.md) — surfaces table, calibration, output schema, skip conditions; load at Step 1.
- [references/envelope-examples.md](references/envelope-examples.md) — successful + blocked envelope variants; load at Step 7.
- [references/edge-cases.md](references/edge-cases.md) — REQ-ID not found, REMOVED still referenced, multiple domains, verify with warnings; load when an unexpected merge condition arises.
- `../_shared/context-protocol.md` — startup sequence; load first.
- `../_shared/persistence-contract.md` — archive copy rules; load at Step 5.
- `../_shared/result-envelope.md` — envelope schema; load at Step 7.
- `../_shared/spec-convention.md` — merge algorithm; load at Step 4.
