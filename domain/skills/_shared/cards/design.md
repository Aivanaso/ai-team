# Card: design

> Read when: `ai-team status` says the task is large and the design is missing or `draft`.

The design is the plan's only source of constraints. It is written **with** the user, on
disk, before any plan exists: `.ai-team/designs/<task>.md`.

## 1. Map pass (scout, mode `map`)

`ai-team acquire scout-map` — one ticket per zone; several may run in parallel. Narrow topic,
no scope proposal. It returns where the flow lives, the existing analogue, documented gotchas,
external conditions the replaced logic gates on, and open questions — every claim `file:line`.
Report: `.ai-team/explorations/<task>-map[-<zone>].md`. Model sonnet, effort medium.
Settle each ticket with the harness figures (card: ingest).

Open questions → questions to the user. Gotchas and conditions → surfaces the design names.

## 2. Brainstorm, then write the file

Two or three approaches, the chosen one and why. YAGNI. Then the file, in this shape
(frontmatter keys in English; section names Spanish or English):

```
---
title: "<what is built, one line>"
created_at: "<ISO UTC>"
status: draft
map_report: ".ai-team/explorations/<task>-map.md"
security: pending | not-needed
---
## Objetivo · ## Contexto · ## Preguntas y respuestas · ## Enfoques considerados
## Diseño  (### Componentes y flujo · ### Errores y casos límite · ### Superficies nombradas  · ### Condiciones externas a conservar)
## Decisiones · ## Seguridad · ## Fuera de alcance · ## Fases
```

- **Superficies nombradas**: one bullet per file, `path:line` or `path (nueva)`.
- **Decisiones**: bullets; invariants, never mechanisms (the rewrite test, card: classify).
- **Fases**: `### Fase N — Title`, then `Entrega:`, `Escenarios:` (bullets, given/when/then),
  `Check:` with the command in backticks. The first phase is visible or runnable on its own.
- No placeholders. Self-review for contradictions, ambiguity, scope before asking for the yes.

## 3. Security gate (only when the design touches a tier-2 surface)

Auth, crypto, secrets, payments, PII, migrations/deletion, untrusted-input parsing, permission
checks, public contracts, a blocking gate of the review plane → `security: pending`, then
`ai-team acquire security-threat-model` (sonnet, high) over the design FILE. Its MUST/SHOULD
requirements are copied into `## Seguridad` as decisions. Otherwise `security: not-needed`
with the reason in `## Seguridad`.

## 4. Approval

Walk the user through **Decisiones** one by one, in their language, before asking. Then:
```
ai-team design approve .ai-team/designs/<task>.md
```
Card: plan.
