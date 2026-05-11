# Commit Message Examples — work-unit-commits

> Load-on-demand reference for Step 4 (message composition). Three worked examples.

## Example 1 — Pure feat group

Group G1 adds a new skill file. All tasks are new functionality.

```
feat(sdd-redesign-v2/G1): add common-rules.md + persistence-contract extensions

Covers: REQ-CR-001, REQ-CR-002, REQ-CR-003, REQ-CR-004, REQ-CR-005, REQ-CR-006, REQ-CR-007, REQ-WUC-007
```

- `type`: `feat` — all tasks create new content
- `scope`: `{change-name}/G{N}` — `sdd-redesign-v2/G1`
- Subject is 62 chars — within the 72-char limit
- Body lists all REQ-IDs covered by tasks in this group

## Example 2 — Mixed feat+fix group with subject truncation

Group G3 modifies 5 SKILL.md files and one task required an out-of-plan fix (logged in decisions[]). The natural subject line would be 79 chars; truncation is required.

**Before truncation (79 chars — TOO LONG):**
```
feat(sdd-redesign-v2/G3): refactor 5 SKILL.md files + remove duplicate rules
```

**After truncation with WARNING:**
```
feat(sdd-redesign-v2/G3): refactor 5 SKILL.md files, remove duplicate rules

Covers: REQ-CR-007, REQ-TASKS-019, REQ-APPLY-021, REQ-ARCHIVE-002, REQ-SCOUT-015
```

Envelope includes:
```yaml
risks:
  - "WARNING: commit subject truncated from 79 to 72 chars — review for clarity"
```

## Example 3 — Project-skill override

The project has `{project_root}/.claude/skills/commit/SKILL.md` which mandates a different scope token format: `[PROJ-NNN] {description}` instead of `{change-name}/G{N}`.

**Default (REQ-WUC-005):**
```
feat(sdd-redesign-v2/G5): update references/ files for redesigned skills
```

**Project-skill override applied:**
```
feat[ECO-1234]: update references/ files for redesigned skills

Covers: REQ-TASKS-012, REQ-APPLY-014, REQ-VERIFY-006
```

Envelope includes:
```yaml
risks:
  - "WARNING: project commit skill overrode scope token — applied [ECO-1234] instead of default (sdd-redesign-v2/G5)"
```

Note: the project skill's scope token replaces the parenthetical scope; the `type:` and `Covers:` body remain from REQ-WUC-005 as the floor.
