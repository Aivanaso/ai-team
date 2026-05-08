# Decisions Log Examples — sdd-apply

> Worked examples of mid-flight decision entries. Load when you need to write a `decisions:` entry in `state.yaml`.

These examples illustrate the three most common entry types: an out-of-plan fix, a design pivot, and a task-level deviation with a commit SHA.

---

## Example 1 — Out-of-Plan Fix (`task_ref: "out-of-plan"`)

**Scenario:** While implementing Task 2.3 (add YAML frontmatter to SKILL.md), the agent noticed that the `scripts/install.sh` was silently ignoring a copy failure. This was not in any task but had to be fixed or the next smoke test would fail.

```yaml
decisions:
  - date: 2026-05-08T20:30:00Z
    phase: apply
    task_ref: "out-of-plan"
    decision: "Add explicit error handling to cp command in install.sh"
    reason: "Smoke test 3 would silently succeed even when references/ copy failed; the fix is 2 lines and blocks a regression"
    evidence: "scripts/install.sh:47 — `cp -R \"$dir.\" \"$dest/\" 2>/dev/null` swallows cp exit code; running the negative test showed verify_install never triggered"
    commits: ["b6ec5cf"]
```

---

## Example 2 — Design Pivot (`task_ref: "design-pivot"`)

**Scenario:** The design specified shipping 10 pull requests. During apply the agent pivoted to direct-to-main atomic commits (one per PR slice).

```yaml
decisions:
  - date: 2026-05-08T19:35:00Z
    phase: apply
    task_ref: "design-pivot"
    decision: "Switch from 10 PRs (DD-7) to direct-to-main with 10 atomic commits"
    reason: "Personal repo, no reviewers; atomicity preserved at commit level (revertible per skill); UI overhead of 10 PRs not justified"
    evidence: "User decision at apply approval gate (orchestrator session 2026-05-08)"
    commits: ["b6ec5cf"]
```

---

## Example 3 — Task-Level Deviation with SHA (`task_ref: "T1.5"`)

**Scenario:** Task 1.5 called for a bash experiment script. The tasks.md specified the script path as `.ai-team/changes/sdd-llm-first/picker-flag-experiment.sh`. The agent discovered that `$HOME` was unexpanded in the here-doc and had to substitute the literal path.

```yaml
decisions:
  - date: 2026-05-08T21:00:00Z
    phase: apply
    task_ref: "1.5"
    decision: "Replace $HOME with literal path in picker-flag-experiment.sh here-doc"
    reason: "$HOME is not expanded inside a quoted here-doc; the dummy skill landed at the wrong path without this fix"
    evidence: "bash -x picker-flag-experiment.sh shows DUMMY_DIR='/home/ivan/.claude/skills/_picker-test' but mkdir followed by cat produced empty SKILL.md at literal '$HOME' path"
    commits: ["b6ec5cf"]
```

---

## When NOT to write an entry

Trivial within-task corrections do not need entries:

- Fixing a typo in a variable name caught immediately.
- Adding a missing semicolon found by the compiler.
- Reordering imports to satisfy linting rules.
- Adjusting whitespace / line endings.

The bar is: **"does this deviate from the approved plan?"** If yes, log it. If it's just mechanical correction within the bounds of the task, skip it.
