# Audit Report Output Template

Use this template when writing `{change_dir}/audit-report.md` in Step 9.4.

## Template

```markdown
# Audit Report: {change-name}

**Date:** {ISO 8601}
**Mode:** code-audit
**Branch:** {change_branch}
**Base:** {base_branch}

## Summary

{1-3 sentences overall assessment}

## Diff Scope

Files audited: {list from git diff --name-only}
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
{findings or "No findings" — every guard the diff introduces has its executor (CI step, script entry, registration) in the same diff}

## Dependency Auditor

{output of test_commands.security, or "Dependency auditor: not configured (skipped)"}

## Suppression Tally

{N} findings suppressed (confidence < 80%). Reasons: {brief list, or "none"}
```

## Per-Finding Structure

Each finding MUST include all seven fields:

| Field | Description |
|-------|-------------|
| `id` | F-1, F-2, ... (sequential, stable within a single artifact) |
| `category` | One of the 5 vulnerability categories or `enforcement-wiring` |
| `file_line` | `path/to/file.ts:42` — mandatory per Evidence Protocol Rule 1 |
| `severity` | CRITICAL \| WARNING \| SUGGESTION |
| `description` | 1-3 sentences: what the issue is |
| `exploit_scenario` | One paragraph: how an attacker would use this |
| `recommendation` | One paragraph or fix snippet |
| `confidence_rationale` | One sentence: why > 80% confidence |

## base_branch Semantics

`base_branch` MUST be the merge-base of the change branch relative to main, NOT simply "main". The orchestrator computes this with `git merge-base main {change_branch}` and injects the resulting SHA. Use the `base_branch` SHA injected by the orchestrator (recomputing it would expand the diff scope to the full branch history).
