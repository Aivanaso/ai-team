# Envelope Examples — work-unit-commits

> Load-on-demand reference for Step 10. Four envelope variants covering the main outcomes.

## ok (auto mode)

```yaml
status: ok
executive_summary: "Committed G1 (2 tasks, 3 files) — SHA abc1234ef"
mode: auto
commit_sha: "abc1234ef"
group_id: "G1"
artifacts:
  - name: "G1 commit"
    path: "git:abc1234ef"
risks: []
model_used: "sonnet"
context_resolution: "injected"
```

State update (auto mode):
```yaml
phases:
  apply:
    commits:
      "G1": "abc1234ef"
```

## ok (manual mode)

```yaml
status: ok
executive_summary: "Manual commit prepared for G2 — run the commands in manual_commit.commands"
mode: manual
manual_commit:
  message: "feat(sdd-redesign-v2/G2): add work-unit-commits skill\n\nCovers: REQ-WUC-001, REQ-WUC-002, REQ-WUC-003"
  files:
    - "domain/skills/work-unit-commits/SKILL.md"
    - "domain/skills/work-unit-commits/references/envelope-examples.md"
    - "domain/skills/work-unit-commits/references/commit-message-examples.md"
    - "domain/skills/work-unit-commits/references/edge-cases.md"
  commands:
    - "git add domain/skills/work-unit-commits/SKILL.md"
    - "git add domain/skills/work-unit-commits/references/envelope-examples.md"
    - "git add domain/skills/work-unit-commits/references/commit-message-examples.md"
    - "git add domain/skills/work-unit-commits/references/edge-cases.md"
    - "git commit -m 'feat(sdd-redesign-v2/G2): add work-unit-commits skill'"
group_id: "G2"
risks:
  - "WARNING: manual mode — user must run commands before state.yaml.commits[G2] is populated"
model_used: "sonnet"
context_resolution: "injected"
```

State update (manual mode):
```yaml
phases:
  apply:
    commits:
      "G2": "manual-pending"
```

## failed (hook reject)

```yaml
status: failed
executive_summary: "pre-commit hook rejected commit for G1 — see risks"
mode: auto
group_id: "G1"
artifacts: []
risks:
  - "pre-commit hook rejected: eslint found 2 errors in domain/skills/work-unit-commits/SKILL.md"
  - "git output: husky > pre-commit hook failed (add --no-verify to bypass)"
model_used: "sonnet"
context_resolution: "injected"
```

## blocked (config missing)

```yaml
status: blocked
executive_summary: "config.yaml not found — cannot determine commit_strategy"
group_id: null
artifacts: []
risks:
  - "Expected .ai-team/config.yaml at project root; file not found"
model_used: "sonnet"
context_resolution: "injected"
```
