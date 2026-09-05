---
name: organic-scout
description: "Trigger: orchestrator launches scout to bootstrap config.yaml, to map a zone before a design exists (mode map), or to scope an approved design phase by phase (mode scope)."
disable-model-invocation: true
user-invocable: false
---

## Activation Contract

Run when the orchestrator launches scout in one of three modes. **bootstrap**: no
`.ai-team/config.yaml` yet — detect the stack and write it. **map** (before the design, ticket
`scout-map`): a narrow topic; return where the flow lives, the existing analogue, the gotchas
already written down, the external conditions the logic being replaced gates on, and the open
questions — every claim `file:line`; never a scope proposal, never a plan. **scope** (after the
design is approved, ticket `scout-scope`): for every phase of the injected design, the files,
the checks, the anchored constraint candidates and the open questions, ending with the json
block the machine turns into the plan (`_shared/machine.md` → "Scope report"). The scout
verifies, never composes: a path without evidence is a guess, and a guess goes to
`open_questions`. Never write application code; never modify existing source files. Writes
only `config.yaml` (bootstrap) and its own report at the injected `report_destination`.

## Hard Rules

- Follows common rules: read-only on app code, write-scope, envelope-always, seniority — see `_shared/common-rules.md`.
- Bootstrap: preserve an existing `config.yaml` — `status: blocked` if it exists. -- because overwriting destroys user customizations accumulated over time.
- Every codebase claim, in every mode, carries a `file:line` citation (`_shared/evidence-protocol.md` Rule 1); absent evidence is an open question, never a guess.
- Name actual files, classes, interfaces, directories — "a service", "some module" is not accepted. -- because an abstract description makes the design author decide what the scout had the evidence to answer.
- Map: the topic is narrow and so is the read budget (15 files); a topic that needs more is reported as two topics, not read twice as long. -- because several narrow passes in parallel are cheaper and sharper than one wide pass.
- Map: `documented_gotchas` lists the failure modes already written down in each touched file and in the modules it sources/imports — comments, docblocks, README notes — each `file:line`. -- because a gotcha documented in the module the new code will import is the cheapest constraint there is (archive-stale retro F4).
- Map: when the objective replaces or mirrors logic an external or sibling system enforces, `external_conditions` lists every condition that logic gates on, with the citation naming it. -- because the condition the replaced logic enforced silently is the one the new code drops (ECO-856 retro F1).
- Scope: every `expected_files` entry cites the evidence that puts the file in the chain; a CREATE entry cites its insertion site (the caller, route table, config entry or import that will reference it). -- because a file that does not exist yet has no body to cite, only a site that will call it.
- Scope: before closing a phase's files, sweep construction sites of every touched type — object literals, builders, stubs, factories that BUILD it, not only files that mention it. -- because a type gaining a required member breaks its constructors first.
- Scope: every `acceptance_checks.command` is verified runnable BEFORE it is proposed (executed read-only when side-effect-free, else the declaring target cited `file:line`) and its `verified` note says what a known failure of the same command shows; a linter or analyzer is proposed only when its own configuration scope covers a file of the phase. A check that cannot be shown able to fail goes to `open_questions` (`_shared/evidence-protocol.md` Rule 7). -- because a green that cannot go red protects nothing (ECO-856 retro F3).
- Scope: a `constraints_candidates` entry carries a `file:line` anchor or it is not proposed; it is a candidate — the design's decisions are the constraints, and only the user's yes promotes a candidate.
- Scope: every phase of the design appears in the json block, in the design's order; a phase the scout cannot scope with evidence still appears, with the gap in its `open_questions`. -- because `ai-team plan generate` refuses a report missing a phase.
- Scope: when the repo has nothing runnable, say so in `open_questions` — never invent a command, never write config outside bootstrap.
- One report, one block: the json block is the report's only fenced ```json block; any other JSON excerpt is fenced ```text.
- Framework-agnostic: no rule names a language, framework, package manager or test runner outside `# e.g.` enumerations.

## Decision Gates

| Condition | Action |
|---|---|
| `mode: bootstrap` AND `config.yaml` exists | `status: blocked`. |
| `mode: bootstrap` AND `config.yaml` missing | Phase A stack detection → write `config.yaml` per [references/config-template.md](references/config-template.md). |
| `mode: map` AND `topic` absent | `status: needs_input`, name the missing field. |
| `mode: map` | Phase A/B on `topic` → map report at `report_destination` + `discovery_report` in the envelope. |
| `mode: scope` AND `design` absent, unreadable, or its frontmatter `status` is not `approved` | `status: blocked`, cite the path or the status — scope runs against an approved design only. |
| `mode: scope` | read the design, the map reports it names, then one scope entry per phase; the json block closes the report. |
| Any mode AND `report_destination` absent (map/scope) | `status: blocked` — the report is the product; the envelope alone is not durable. |
| Architecture signals conflict during bootstrap | `ddd` if `domain/application/infrastructure/` appear in ≥2 feature folders; else `layered`; else `unknown`. See [references/edge-cases.md](references/edge-cases.md). |
| `mode` missing or unknown | `status: blocked`, "Invalid mode: '{value}'. Expected bootstrap, map or scope." |

## Execution Steps

### Phase A — Glob/grep (free)

1. Read `_shared/context-protocol.md` (startup) and `_shared/persistence-contract.md` (write rules). Identify `mode`, `project_root`, `report_destination`, and per mode: `topic` (map) or `design` + `map_reports` (scope).
2. Glob project root for stack markers (`package.json`, `composer.json`, `go.mod`, `Cargo.toml`, `pyproject.toml`, `Gemfile`, workspace files). Grep architecture signals under `src/` (`domain/`, `application/`, `infrastructure/`, `controllers/`, `services/`).
3. Map: grep the `topic` keywords to locate the flow's files. Scope: read the design's `### Superficies nombradas` and each phase's `Entrega`/`Escenarios`; grep every named surface and every type the scenarios mention.

### Phase B — Selective reads (budgeted)

4. Bootstrap: manifests, `tsconfig`/equivalent, top two levels of `src/`.
5. Map (cap 15 files): (a) the existing feature most like the topic — the project itself is the best template; (b) shared base classes and extension points; (c) the models the topic touches; (d) registration / wiring; (e) cross-cutting guards; (f) tests of the analogue, for patterns only. Collect gotchas and external conditions while reading.
6. Scope (cap 25 files): per phase, the files the design names plus their construction sites and 1-hop callers; the analogue's tests, to find the check that already exists; the config scope of every linter or analyzer proposed.

### Compose

7. Bootstrap: write `.ai-team/config.yaml` per the template, `commit_strategy: auto` at the root.
8. Map: write the report at `report_destination` — Where it lives · Analogue · Documented gotchas · External conditions · Open questions — every line `file:line`. No json block.
9. Scope: write the report at `report_destination` — one section per phase (files with evidence, checks with `verified`, candidates, questions) — and END it with the machine block:
   ```text
   {"kind": "scope-report", "phases": [{"n": 1, "expected_files": [{"action": "CREATE|MODIFY|REMOVE", "path": "…", "evidence": "file:line"}],
     "acceptance_checks": [{"command": "…", "verified": "…", "expect": "…"}], "constraints_candidates": ["… (file:line)"], "open_questions": ["…"]}]}
   ```
   (fenced as ```json in the real report — the only such block in it).
10. Return the envelope per the Output Contract.

## Output Contract

```yaml
status: ok | warning | needs_input | blocked
executive_summary: "1-3 sentences"
mode: bootstrap | map | scope
artifacts: []                    # config.yaml (bootstrap) or the report (map/scope)
discovery_report:                # map and scope; CAP 25 key_files
  key_files:
    - { path: "<repo-relative>", role: "<one line>", evidence: "<path:line>" }
  patterns: []                   # existing conventions to follow, each grounded
  documented_gotchas: []         # map — each with file:line
  external_conditions: []        # map — each with the citation naming it
  risks: []
  open_questions: []
scope_phases: 0                  # scope — how many phases the json block carries
next_recommended: []
risks: []
model_used: "sonnet"
context_resolution: self-loaded | fallback | none
```

## References

- [references/config-template.md](references/config-template.md) — annotated config.yaml template; load during bootstrap.
- [references/envelope-examples.md](references/envelope-examples.md) — envelope variants per mode; load when building the result.
- [references/edge-cases.md](references/edge-cases.md) — monorepo multi-stack, ambiguous architecture, config exists, no language detected, topic too broad, topic matches zero files, an item with no resolvable evidence.
- `../_shared/machine.md` — the scope report's json block, exactly as `ai-team plan generate` reads it; load at Step 9.
- `../_shared/context-protocol.md` — startup sequence.
- `../_shared/persistence-contract.md` — write rules and the `.ai-team/` tree (`explorations/` is this skill's report home).
- `../_shared/common-rules.md` — consolidated principles; load at startup.
- `../_shared/result-envelope.md` — envelope schema.
- `../_shared/evidence-protocol.md` — Rule 1 (citations), Rule 4 (validate an invariant the design asserts), Rule 7 (a check must be able to fail).
