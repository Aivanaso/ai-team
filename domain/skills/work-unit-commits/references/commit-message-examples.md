# Commit Message Examples — work-unit-commits

> Load-on-demand reference for Step 6 (message composition). Three worked examples.

## Example 1 — Pure feat group

The Task Brief `billing-export` adds a new endpoint. All declared files are new functionality.

```
feat(billing-export): add billing export endpoint + smoke test

Files: services/billing/export.py, tests/billing/test_export.py
```

- `type`: `feat` — all files are new functionality
- `scope`: `{group_id}` — the brief-slug label, `billing-export`
- Subject is 47 chars — within the 72-char limit
- Body lists the files the commit covers

## Example 2 — Mixed feat+fix group with subject truncation

Group `invoice-refactor` modifies 5 files, including a fix the implementer folded into the
same candidate. The natural subject line would be 79 chars; truncation is required.

**Before truncation (79 chars — TOO LONG):**
```
feat(invoice-refactor): refactor 5 billing files + fix duplicate line-item rule
```

**After truncation with WARNING:**
```
feat(invoice-refactor): refactor 5 billing files, fix duplicate line-item rule

Files: services/billing/invoice.py, services/billing/lines.py, services/billing/tax.py,
tests/billing/test_invoice.py, tests/billing/test_lines.py
```

Envelope includes:
```yaml
risks:
  - "WARNING: commit subject truncated from 79 to 72 chars — review for clarity"
```

## Example 3 — Project-skill override

The project has `{project_root}/.claude/skills/commit/SKILL.md` which mandates a different
scope token format: `[PROJ-NNN] {description}` instead of `{group_id}`.

**Default:**
```
feat(api-cleanup): update references/ files for the renamed client
```

**Project-skill override applied:**
```
feat[ECO-1234]: update references/ files for the renamed client

Files: services/api/client.py, tests/api/test_client.py
```

Envelope includes:
```yaml
risks:
  - "WARNING: project commit skill overrode scope token — applied [ECO-1234] instead of default (api-cleanup)"
```

Note: the project skill's scope token replaces the parenthetical scope; the `type:` and file
body remain from the default composition rule as the floor.
