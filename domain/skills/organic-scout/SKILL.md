---
name: organic-scout
description: "Trigger: orchestrator launches scout for bootstrap (no config.yaml), pre-brief discovery, or on-demand inspection."
disable-model-invocation: true
user-invocable: false
---

## Activation Contract

Run when the orchestrator launches scout at the start of a new project (no `config.yaml`
yet), before a Large or unclear-scope Task Brief when the user accepted the optional
discovery offer, or on demand for open-ended project inspection. Two modes: **bootstrap**
detects the project stack and generates `config.yaml`; **discover** investigates a topic or
objective and returns a discovery report — key files, structure, existing patterns to
follow, and risks, grounded in read evidence with `file:line` citations. Never write
application code. Never modify existing source files. Writes only `config.yaml` (bootstrap
mode) and its own report at an injected `report_destination` (discover mode) — never
`design.md`, and never under `.ai-team/briefs/` (Brief Files are orchestrator-authored only).

## Hard Rules

- Follows common rules: read-only on app code, write-scope, envelope-always, seniority — see `_shared/common-rules.md`.
- Bootstrap: preserve existing `config.yaml` — return `status: blocked` if it already exists (user customizations accumulated across prior sessions must not be lost). -- because overwriting destroys user customizations (test runner paths, language versions, project conventions) accumulated over time.
- Bootstrap writes a `commit_strategy: auto` field at the root of generated `config.yaml`. Existing configs without the field are valid (backward-compatible default).
- Config evolution for existing projects is owned exclusively by the orchestrator's Config Refresh Check; scout writes `config.yaml` only on first bootstrap. -- because a single additive owner keeps user customizations safe — two writers of the same file with different merge semantics would race.
- Discover: ground every codebase claim in read evidence with a `file:line` citation (Evidence Protocol Rule 1); an unfamiliar pattern or absent evidence is surfaced as an open question, never guessed.
- Discover: name actual files, classes, interfaces, and directories. Abstract descriptions ("a service", "some module") are not accepted. -- because abstract descriptions force the Task Brief author to make decisions scout had the evidence to answer.
- Discover: follow existing project patterns in the report's recommendations — if the project uses a repository pattern, the report names it as the pattern to follow; it does not propose a new paradigm the discovery request did not ask for.
- Discover: `report_destination` is always injected by the orchestrator for a discovery pass that feeds a Task Brief or otherwise counts as review-plane/scope-authority material (Critical Context Forwarding, `orchestrator-protocol.md`) — write the report there; an absent injection is degradation, not a design choice: report `context_resolution: fallback` and flag the gap in `risks`. An on-demand inspection that feeds no brief may omit the injection — the report then returns in the result envelope only, and the orchestrator folds it directly into whatever it composes next.
- Discover, scope_proposal: when the orchestrator injects `scope_proposal: true`, every `expected_files` entry in the proposal carries its own `file:line` evidence — a path without evidence is not a proposal, it is a guess.
- Discover, scope_proposal: every proposed `acceptance_checks.command` is verified runnable BEFORE proposing it — execute it read-only when side-effect-free, otherwise cite the declaring target's existence (e.g. the `targets` block of a `project.json`, a script in `package.json`/`Makefile`) with `file:line`. An unrunnable check protects nothing and burns a delegation round.
- Discover, scope_proposal: before closing `expected_files`, sweep construction sites of every touched type/interface — grep for object literals, builders, stubs, and factories that build it, not only files that annotate or mention it. A type gaining a required member breaks its constructors first.
- Discover, scope_proposal: trace the objective's chain to the leaves — if the report's prose describes a data/control flow, every link of that flow appears in `expected_files`, or in `open_scope_questions` with the reason it could not be closed.
- Discover, scope_proposal: a `constraints_candidates` entry without a `file:line` anchor is not proposed — the same evidence discipline as `expected_files`.

## Decision Gates

| Condition | Action |
|---|---|
| `mode: bootstrap` AND `config.yaml` already exists | Return `status: blocked`. |
| `mode: bootstrap` AND `config.yaml` missing | Run Phase A stack detection → write `config.yaml` per [references/config-template.md](references/config-template.md). |
| `mode: discover` | Run Phase A/B scoped to `topic` → return a discovery report in the envelope. |
| `mode: discover` AND `scope_proposal: true` injected | Produce the discovery report AND the `scope_proposal` block (Output Contract); a chain link with no resolvable evidence goes in `open_scope_questions` — never silently omitted. |
| `mode` missing, or `topic` absent in discover mode | Recover from user-facing prompt text if possible; else `status: needs_input`, `context_resolution: fallback`, flag in envelope. |
| Architecture signals conflict during bootstrap | Default to `ddd` if `domain/application/infrastructure/` appear in ≥2 feature folders; else `layered`; else `unknown`. See [references/edge-cases.md](references/edge-cases.md). |

## Execution Steps

### Phase A — Glob/grep (free, no token budget)

1. Read `_shared/context-protocol.md` (startup) and `_shared/persistence-contract.md` (write rules — loaded per common-rules Principle 5; this skill writes `.ai-team/config.yaml` only in bootstrap mode). Identify mode from injected context (`mode:`, `project_root`, plus `topic` and the optional `scope_proposal: true` flag in discover mode).
2. Glob project root for stack markers: `package.json`, `composer.json`, `go.mod`, `Cargo.toml`, `pyproject.toml`, `Gemfile`, `turbo.json`, `pnpm-workspace.yaml`, `lerna.json`. Detect language, framework, package manager, monorepo status from these files without reading them fully (names suffice for a first pass).
3. Grep for architecture signals: directory names `domain/`, `application/`, `infrastructure/`, `controllers/`, `services/`, `entities/` under `src/`. Grep for code patterns: `*Command.ts`, `*Handler.ts`, `*Event.ts`, `*Repository.ts`, `*Saga.ts`.
4. Discover mode: grep for `topic` keywords to locate relevant files (controllers, services, entities, DTOs, test files, pages/components).

### Phase B — Selective reads (budgeted, max 15–25 files)

5. **Bootstrap**: read `package.json` (if Node.js) for `name`, `workspaces`, framework deps. Read `tsconfig.json` for `strict`, path aliases. Scan top 2 levels of `src/` directory tree.
6. **Discover**: read the most relevant files (ranked by keyword match density) in priority order: (a) an existing feature similar to the one the topic describes — the best template is the project itself; (b) shared base classes, interfaces, abstract types (extension points); (c) entity/model definitions the topic touches; (d) module registration / dependency injection setup; (e) middleware, guards, interceptors, pipes (cross-cutting concerns); (f) existing tests for similar features (patterns only, not individual cases). Cap at 15 files for a narrow topic, 25 for a full pre-brief pass.

### Compose output

7. **Bootstrap**: generate `.ai-team/config.yaml` using [references/config-template.md](references/config-template.md). In addition to existing fields, write `commit_strategy: auto` at the root level. This is mandatory for new bootstraps. Language detection heuristics:
   - Monorepo: `turbo.json` OR `pnpm-workspace.yaml` OR `lerna.json` OR `workspaces` field in `package.json` OR multiple package manifests in direct child dirs.
   - App vs library: `main.ts`/routes/controllers → `app`; `package.json` with `main`/`exports`/`types` and no server code → `library`.
   - Package manager lock file precedence: `pnpm-lock.yaml` > `yarn.lock` > `bun.lockb` > `package-lock.json` > `composer.lock`.
8. **Discover**: compose the discovery report — Key Files (path, role, `file:line` evidence), Patterns Observed (existing conventions the Task Brief should follow), Risks (grounded citations), Open Questions (claims with no resolvable evidence). When the orchestrator injected `scope_proposal: true`, additionally compose the `scope_proposal` block: cite `file:line` evidence for every `expected_files` entry, verify each `acceptance_checks.command` runnable before proposing it, sweep construction sites for every touched type, name each seam's `public_contracts`, and name any evidence-derived `constraints_candidates` (optional — never invented). Return it all in the envelope's `discovery_report` field. When `report_destination` is injected, also write it there (create its parent directory if absent).
9. Return the envelope per Output Contract.

## Output Contract

- Bootstrap: writes `.ai-team/config.yaml`. `context_resolution: none`.
- Discover: writes the report at the injected `report_destination` (resolved relative to `project_root`) — mandatory from the orchestrator's side for every discovery pass that feeds a Task Brief or otherwise counts as review-plane/scope-authority material (Critical Context Forwarding); optional only from this skill's own write step, i.e. it writes nothing when no destination is injected. `context_resolution: self-loaded` (or `fallback` when the injection is absent and the pass was review-plane material).

```yaml
status: ok | warning | needs_input | blocked
executive_summary: "1-3 sentences"
artifacts: []                    # config.yaml entry (bootstrap) or report entry (discover, only if report_destination given)
discovery_report:                # discover mode only
  key_files:                     # CAP 25 entries
    - { path: "<repo-relative path>", role: "<one line>", evidence: "<path:line>" }
  patterns: []                   # existing conventions to follow, each grounded
  risks: []
  open_questions: []
  scope_proposal:                # discover mode, only when the orchestrator requests it (scope_proposal: true)
    expected_files:
      - { action: CREATE|MODIFY|REMOVE, path: "<repo-relative>", evidence: "<path:line — why this file is in the chain>" }
    construction_sites_swept: true # object literals, builders, stubs, factories that BUILD the touched types were grepped — not just annotations/mentions
    acceptance_checks:
      - { command: "<verbatim>", verified: "<how runnability was proven: executed read-only | target exists at path:line>", expect: "<observable outcome>" }
    public_contracts:            # what the change creates/modifies/deletes at its seams
      - "<one line each: signatures, events + fields, named test cases, DB schema, user-visible copy — with a file:line anchor>"
    constraints_candidates:      # optional — an existing invariant/pattern/decision the objective must honor, evidence-derived, never invented
      - "<one line — an existing invariant/pattern/decision the objective must honor, with file:line>"
    open_scope_questions: []     # anything the scout could not close with evidence
next_recommended: []
risks: []
model_used: "sonnet"
context_resolution: self-loaded | fallback | none
```

## References

- [references/config-template.md](references/config-template.md) — annotated config.yaml template; load during bootstrap when generating config.
- [references/envelope-examples.md](references/envelope-examples.md) — envelope variants per mode; load when building the result envelope.
- [references/edge-cases.md](references/edge-cases.md) — monorepo multi-stack, ambiguous architecture, config.yaml exists, no language detected, topic too broad, topic matches zero files; load when encountering non-happy-path conditions.
- `../_shared/context-protocol.md` — startup sequence.
- `../_shared/persistence-contract.md` — write rules (loaded per common-rules Principle 5; this skill writes `.ai-team/config.yaml` only in bootstrap mode).
- `../_shared/common-rules.md` — consolidated principles (read-only, write-scope, envelope-always, seniority); load at startup.
- `../_shared/result-envelope.md` — envelope schema.
- `../_shared/evidence-protocol.md` — Rule 1 (file:line citation mandatory for every codebase claim).
