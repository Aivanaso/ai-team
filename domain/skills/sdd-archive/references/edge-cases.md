# Edge Cases — sdd-archive

> Loaded by sdd-archive when an unexpected condition arises during merge or archive operations.

### REQ-ID Not Found in Base Spec

If a MODIFIED requirement references a REQ-ID that doesn't exist in the base spec:

- Treat it as ADDED instead (the base spec may have been manually edited).
- Note in the result: "REQ-{ID} not found in base -- treated as new requirement."

### REMOVED Requirement Still Referenced

If a REMOVED requirement is referenced by other requirements in the base spec (via Dependencies section):

- Still remove it (the delta is authoritative).
- Add a WARNING in the result: "REQ-{ID} removed but referenced by REQ-{other-ID}. Update dependency references."

### Multiple Domains

Process each domain's delta spec independently. The merge for domain A does not affect domain B. Order of processing does not matter; domains are isolated.

### Verify Passed With Warnings

If verify verdict is PASS WITH WARNINGS:

- Proceed with archive normally.
- Carry the warnings into the result envelope as `risks`.
- The orchestrator already approved proceeding despite warnings.

### Archive Name Collision

If an archive directory with the same name already exists (re-archive after fix cycle):

- Append a counter: `YYYY-MM-DD-{change-name}-2`, `-3`, and so on.
- Never overwrite an existing archive.

### Empty Base Spec Directory

If `.ai-team/specs/` doesn't exist:

- Create it.
- Create `.ai-team/specs/{domain}/` for each domain in the delta.

### Delta Spec Has No Base (First Change for Domain)

If no base spec exists for a delta domain:

- The delta IS the base spec. Copy it to `.ai-team/specs/{domain}/spec.md`, removing the ADDED/MODIFIED/REMOVED section headers (it becomes a flat spec).

### No Delta Specs (skip-spec infra path)

If the change had no spec phase (`skip_spec: true`):

- Skip Step 3 (merge) entirely. Note: "No delta specs to merge."
- Proceed directly to Step 4 (copy to archive).
