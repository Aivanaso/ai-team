# Envelope Examples — work-unit-commits

> Load-on-demand reference for Step 8. Four envelope variants covering the main outcomes.

## ok (auto mode)

```yaml
status: ok
executive_summary: "Committed billing-export (2 files) — SHA abc1234ef"
mode: auto
commit_sha: "abc1234ef"
group_id: "billing-export"
artifacts:
  - name: "billing-export commit"
    path: "git:abc1234ef"
risks: []
model_used: "sonnet"
context_resolution: "self-loaded"
```

## ok (manual mode)

```yaml
status: ok
executive_summary: "Manual commit prepared for invoice-refactor — run the commands in manual_commit.commands"
mode: manual
manual_commit:
  message: "feat(invoice-refactor): add pro-rata line-item calculation"
  files:
    - "services/billing/invoice.py"
    - "tests/billing/test_invoice.py"
  commands:
    - "git add services/billing/invoice.py"
    - "git add tests/billing/test_invoice.py"
    - "git commit -m 'feat(invoice-refactor): add pro-rata line-item calculation'"
group_id: "invoice-refactor"
risks:
  - "WARNING: manual mode — user must run the listed commands; no commit exists yet"
model_used: "sonnet"
context_resolution: "self-loaded"
```

## failed (hook reject)

```yaml
status: failed
executive_summary: "pre-commit hook rejected commit for billing-export — see risks"
mode: auto
group_id: "billing-export"
artifacts: []
risks:
  - "pre-commit hook rejected: eslint found 2 errors in services/billing/export.py"
  - "git output: husky > pre-commit hook failed (add --no-verify to bypass)"
model_used: "sonnet"
context_resolution: "self-loaded"
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
context_resolution: "self-loaded"
```
