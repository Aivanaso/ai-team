# SKILL.md Style Guide

## Purpose

SKILL.md is a **runtime contract for the sub-agent**, not human documentation. The reader at delegation time is the LLM in the moment of execution — it reads the file once, acts, and is discarded. Every line must earn its place by guiding that single execution. Background prose, motivation paragraphs, and "nice to know" sections inflate the context window without changing the outcome. Extract them or delete them.

---

## Mandatory Section Order

Every SKILL.md must contain exactly these six `##` sections, in this order:

1. **Activation Contract** — when the orchestrator invokes this skill (trigger conditions, never-run conditions). One paragraph or a short bulleted list. Decides whether to run at all.
2. **Hard Rules** — numbered, absolute constraints the agent must never violate. No prose. If a rule needs explanation, the explanation goes in `references/`.
3. **Decision Gates** — blocking checks before execution begins. Format: `IF <condition> THEN <action>`. Explicit exit conditions only.
4. **Execution Steps** — ordered numbered list. Imperative voice. One step = one action. Sub-steps allowed. Nest with sub-steps (a., b., c.) for multi-action steps; prose paragraphs within steps reduce scannability and belong in references/.
5. **Output Contract** — what the envelope looks like, required fields, mandatory grep-contracts. No envelope examples inline (those go to `references/envelope-examples.md`).
6. **References** — list of `references/` files with a one-line "load when" annotation each. Empty section is fine if no references exist yet.

The six sections above are the complete and fixed structure. Additional sections go in `references/` files; reordering breaks the structural grep contracts in sdd-verify.

---

## What Stays Inline

The following items MUST remain in the SKILL.md body and must NOT be moved to `references/`:

- **9 security touchpoint slugs** (verbatim, `auth/authz` with slash; the other 8 with dashes): `auth/authz`, `crypto`, `deserialization`, `file-io-uploads`, `network-ssrf`, `db-direct-input`, `new-dependencies`, `env-secrets`, `regex-external-input`
- **Severity vocabulary**: `CRITICAL` / `WARNING` / `SUGGESTION`
- **Evidence Protocol Rule citations**: Rule 1, Rule 2, Rule 3, Rule 4, Rule 5 (cite by number; full text lives in `evidence-protocol.md`)
- **`decisions:` schema keys**: `phase`, `task_ref`, `decision`, `reason`, `evidence`, `commits`
- **Result envelope canary fields**: `status`, `executive_summary`, `model_used`, `context_resolution`
- **Mode dispatch logic**: if a skill has multiple modes (e.g. security's `threat-model` / `code-audit`; archive's Step 0 surfaces table), the dispatch table stays inline. The mode-specific detail goes to `references/`.

---

## What Moves to `references/`

Extract to `references/` anything that is referenced but not executed inline:

| Content type | Naming convention |
|---|---|
| Long output templates | `{topic}-template.md` |
| Multiple envelope YAML variants | `envelope-examples.md` |
| Extended edge-case prose | `edge-cases.md` |
| Worked examples / illustrative scenarios | `{topic}-examples.md` |
| Lengthy multi-variant report formats | `report-format.md` |
| Calibration tables, output schemas | `{topic}-reference.md` |

Always use relative paths in the `## References` section. Always include a one-line "load when" description per entry.

---

## Imperative Voice Rule

Execution steps use imperative, direct voice. The sub-agent is the subject.

**Correct:**
> Load config.yaml. Check `strict_tdd`. Write envelope to stdout.

**Incorrect:**
> You should consider loading config.yaml. We recommend checking `strict_tdd`. It may be appropriate to write the envelope.

One verb, one action. If a step requires more than two sentences to describe, it is two steps or a reference file.

---

## Line Budget

| Budget | When it applies |
|---|---|
| Hard limit: ≤ 250 lines | Always. `check-skill-budgets.sh` enforces this. Violations block PR merge. |
| Soft target: ≤ 200 lines | For skills under 450 lines before refactor (most phase skills). |

Measured by `wc -l SKILL.md`. The count includes frontmatter, blank lines, and comments. No exceptions — if you need more lines, extract content to `references/`.

---

## Frontmatter Fields

Every SKILL.md must open with a YAML frontmatter block containing exactly these four keys:

```yaml
---
name: sdd-{phase}
description: "Trigger: {one-line activation condition, ≤ 120 chars}"
disable-model-invocation: true
user-invocable: false
---
```

Rules:
- `description` starts with `"Trigger: "` and is ≤ 120 characters total.
- `disable-model-invocation: true` prevents the skill from appearing in UI pickers and model-invocable skill lists.
- `user-invocable: false` prevents direct user invocation via slash commands.
- No additional frontmatter keys.

---

## Content belongs in references/

Extract this content to `references/` files instead:

- Historical notes → extract to `references/` with context about when and why
- Motivation prose → capture as a single WHY clause on the rule (`-- because {failure mode}`)
- `## Background` or `## Context` sections → extract to `references/`
- Multi-paragraph rule explanations → one sentence per rule inline; rest in `references/`
- Code examples longer than 5 lines → move to `references/`
- Commented-out sections → remove or extract to `references/`
- "TODO" or "FIXME" annotations → track in tasks.md, not inline

---

## References Section Format

Each entry in `## References` must follow this exact format:

```
- [references/{topic}.md](references/{topic}.md) — load when {condition}.
```

Rules:
- Always relative paths (no `~/` or absolute paths).
- Always a one-line "load when" condition. The sub-agent uses this to decide whether to read the file for a given execution.
- No blank lines between entries.
- If the section is empty (no reference files yet), keep the heading and add `(none)`.

Example:
```
## References
- [references/envelope-examples.md](references/envelope-examples.md) — load when constructing the result envelope.
- [references/edge-cases.md](references/edge-cases.md) — load when an unexpected scenario arises during execution.
```

---

## Migration Checklist

When refactoring an existing SKILL.md to the LLM-first shape:

1. **Audit sections** — list every `##` section. Identify which match the 6 mandatory sections and which are extras.
2. **Classify content** — for each paragraph/block: is it runtime-critical (stays inline) or reference material (moves to `references/`)?
3. **Extract reference material** — create `references/` files, copy content verbatim during extraction; rewrite only after the extracted file exists.
4. **Rewrite steps in imperative voice** — edit Execution Steps to imperative, one-action-per-step format.
5. **Add frontmatter** — add the 4-key YAML block at the top.
6. **Add `## References` section** — list every extracted file with its "load when" annotation.
7. **Run budget script** — `./scripts/check-skill-budgets.sh`. Must exit 0 for this skill.
8. **Run grep contracts** — verify cross-file vocabulary consistency: security touchpoint slugs, decisions schema keys, envelope canary fields all present where cited.
