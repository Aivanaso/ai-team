# Envelope Examples — work-unit-commits

> Load-on-demand reference for Step 8. Nine envelope variants covering the main outcomes,
> including the five receipt-gate outcomes from the Decision Gates table.

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

## blocked (tier >= 1, receipt missing)

**Scenario:** the delegation prompt declares `tier: 1` (or 2) but no Review Receipt was injected.

```yaml
status: blocked
executive_summary: "tier 1 candidate missing its review receipt — no commit created for billing-export"
group_id: "billing-export"
artifacts: []
risks:
  - "tier 1 candidate missing its review receipt"
model_used: "sonnet"
context_resolution: "self-loaded"
```

## blocked (no tier declaration, no review-off declaration)

**Scenario:** the delegation prompt carries neither a `tier` value nor an explicit "review off" declaration — the commit gate cannot be evaluated.

```yaml
status: blocked
executive_summary: "no tier declaration and no review-off declaration — cannot determine the commit gate for billing-export"
group_id: "billing-export"
artifacts: []
risks:
  - "no tier declaration and no review-off declaration — cannot determine the commit gate"
model_used: "sonnet"
context_resolution: "self-loaded"
```

## blocked (review-blocked verdict, no recorded override)

**Scenario:** the injected Review Receipt carries `verdict: review-blocked` and its `overrides` field is absent or empty — the user has not accepted the finding.

```yaml
status: blocked
executive_summary: "review-blocked with no recorded override — no commit created for billing-export"
group_id: "billing-export"
artifacts: []
risks:
  - "review-blocked with no recorded override"
model_used: "sonnet"
context_resolution: "self-loaded"
```

## blocked (review-blocked verdict, override present but does not cover the blocking CRITICAL)

**Scenario:** the injected Review Receipt carries `verdict: review-blocked` with a CRITICAL finding (`F-2`) in `lenses.security`. The `overrides` field is present but only carries a bulk `finding_ids` entry for two unrelated MINOR findings — a bulk entry can never cover a CRITICAL (`_shared/result-envelope.md` → Review Receipt), so the blocking CRITICAL remains uncovered.

```yaml
status: blocked
executive_summary: "review-blocked: no singular override entry for CRITICAL F-2 (lenses.security) — no commit created for billing-export"
group_id: "billing-export"
artifacts: []
risks:
  - "review-blocked: no singular override entry for CRITICAL F-2 (lenses.security)"
  - "overrides carries only a bulk finding_ids entry for F-4, F-5 (MINOR) — structurally incapable of covering a CRITICAL"
model_used: "sonnet"
context_resolution: "self-loaded"
```

## ok (tier 0 / review off — ordinary policy, no receipt required)

**Scenario:** the delegation prompt declares `tier: 0` (or an explicit "review off" declaration) — no Review Receipt is required, and the commit proceeds under ordinary policy.

```yaml
status: ok
executive_summary: "Committed docs-typo-fix (1 file) under tier 0 — no review receipt required — SHA def5678ab"
mode: auto
commit_sha: "def5678ab"
group_id: "docs-typo-fix"
artifacts:
  - name: "docs-typo-fix commit"
    path: "git:def5678ab"
risks: []
model_used: "sonnet"
context_resolution: "self-loaded"
```
