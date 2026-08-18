# Audit Report Output Template

Use this template when writing `audit-report.md` at the injected `report_destination`.

## Template

```markdown
# Audit Report: {group_id}

**Date:** {ISO 8601}
**Mode:** code-audit

## Summary

{1-3 sentences overall assessment}

## Audit Scope

Files audited: {group_files}
1-hop callers read: {count} / 10 max

## Findings by Category

### 1. Input Validation
{findings or "No findings"}

### 2. Authentication & Authorization
{findings or "No findings"}

### 3. Cryptography & Secrets
{findings or "No findings"}

### 4. Injection & Code Execution
{findings or "No findings"}

### 5. Data Exposure
{findings or "No findings"}

### 6. Enforcement Wiring
{findings or "No findings" — every guard the candidate introduces has its executor (CI step, script entry, registration) in the same candidate}

## Dependency Auditor

{output of test_commands.security, or "Dependency auditor: not configured (skipped)"}
```

## Per-Finding Structure

Each finding MUST include all nine fields:

| Field | Description |
|-------|-------------|
| `id` | F-1, F-2, ... (sequential, stable within a single artifact) |
| `category` | One of the 5 vulnerability categories or `enforcement-wiring` |
| `file_line` | `path/to/file.ts:42` — mandatory per Evidence Protocol Rule 1 |
| `severity` | CRITICAL \| MAJOR \| MINOR |
| `confidence` | high \| medium \| low — every finding is recorded regardless of confidence (coverage; see SKILL.md Hard Rules) |
| `description` | 1-3 sentences: what the issue is |
| `exploit_scenario` | One paragraph: how an attacker would use this |
| `recommendation` | One paragraph or fix snippet |
| `confidence_rationale` | One sentence: why this confidence level |

## Scope Semantics

`group_files` is resolved relative to the injected `project_root` — this route audits a
declared file set, never a branch diff. There is no `base_branch`/`change_branch` concept on
this route; scope is exactly the Task Brief's candidate files.
