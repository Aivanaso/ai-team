# Envelope Examples

One compact instance per mode. Both follow the Output Contract in `SKILL.md`.

## `retro` mode — `ok`, with one convention proposal drafted

```yaml
status: ok
executive_summary: "Composed the billing-export retro at .ai-team/retros/2026-08-19-billing-export.md; 1 friction (F1) yielded a convention proposal."
mode: retro
artifacts:
  - { name: "retro", path: ".ai-team/retros/2026-08-19-billing-export.md" }
conventions_proposed:
  - { rule: "declare cross-module dependencies in the objective, not just expected_files", why: "the tax-module dependency was knowable at brief-authoring time but surfaced only as a scope-large gate mid-run", good_example: "objective names the shared rounding helper up front", bad_example: "original objective named only the endpoint (Cost Ledger row 1, scope_report.target)", target: "orchestrator-protocol.md#Task Brief" }
proposals_omitted: 0
next_recommended:
  - "apply the accepted proposal to orchestrator-protocol.md's Task Brief element description"
risks: []
model_used: "sonnet"
context_resolution: self-loaded
```

## `retro` mode — `warning`, provisional (Brief File not yet `done`)

```yaml
status: warning
executive_summary: "Composed a PROVISIONAL retro for an active Brief File (status: paused) at the user's request; re-run once the task closes for the durable version."
mode: retro
artifacts:
  - { name: "retro", path: ".ai-team/retros/2026-08-19-billing-export.md" }
conventions_proposed: []
proposals_omitted: 0
next_recommended:
  - "re-run organic-retro (mode: retro) once the Brief File's status flips to done"
risks:
  - "Brief File status is 'paused', not 'done' — Metrics/Close section reflect an incomplete Cost Ledger"
model_used: "sonnet"
context_resolution: self-loaded
```

## `conventions` mode — `ok`

```yaml
status: ok
executive_summary: "Drafted 2 convention proposals from the injected user correction about commit message scope."
mode: conventions
artifacts: []
conventions_proposed:
  - { rule: "commit subject names the touched skill, not the phase number", why: "a phase-numbered subject is meaningless once the phase list changes", good_example: "feat(review): add review_gates objective tool-gate layer", bad_example: "feat: phase 6 changes (user correction, this session)", target: "CLAUDE.md#Git" }
  - { rule: "never reference an internal ticket id in a commit body", why: "commit history outlives the ticket tracker", good_example: "commit 9834adf body describes the change, not a ticket id", bad_example: "prior commit body cited ECO-1165 with no other context (user correction, this session)", target: "CLAUDE.md#Git" }
proposals_omitted: 0
next_recommended: []
risks: []
model_used: "sonnet"
context_resolution: self-loaded
```

## `conventions` mode — `needs_input` (no source material)

```yaml
status: needs_input
executive_summary: "conventions mode invoked with no source_material injected — nothing to draft proposals from."
mode: conventions
artifacts: []
conventions_proposed: []
proposals_omitted: 0
questions:
  - "What correction or friction text should conventions mode draft proposals from?"
next_recommended: []
risks: []
model_used: "sonnet"
context_resolution: self-loaded
```
