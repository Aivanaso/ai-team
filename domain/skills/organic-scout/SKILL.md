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
application code. Never modify existing source files. Never write `design.md` or any
`.ai-team/` artifact other than `config.yaml` (bootstrap only).

## Hard Rules

- Follows common rules: read-only on app code, write-scope, envelope-always, seniority — see `_shared/common-rules.md`.
- Bootstrap: preserve existing `config.yaml` — return `status: blocked` if it already exists (user customizations accumulated across prior sessions must not be lost). -- because overwriting destroys user customizations (test runner paths, language versions, project conventions) accumulated over time.
- Bootstrap writes a `commit_strategy: auto` field at the root of generated `config.yaml`. Existing configs without the field are valid (backward-compatible default).
- Config evolution for existing projects is owned exclusively by the orchestrator's Config Refresh Check; scout writes `config.yaml` only on first bootstrap. -- because a single additive owner keeps user customizations safe — two writers of the same file with different merge semantics would race.
- Discover: ground every codebase claim in read evidence with a `file:line` citation (Evidence Protocol Rule 1); an unfamiliar pattern or absent evidence is surfaced as an open question, never guessed.
- Discover: name actual files, classes, interfaces, and directories. Abstract descriptions ("a service", "some module") are not accepted. -- because abstract descriptions force the Task Brief author to make decisions scout had the evidence to answer.
- Discover: follow existing project patterns in the report's recommendations — if the project uses a repository pattern, the report names it as the pattern to follow; it does not propose a new paradigm the discovery request did not ask for.
- Discover: the report is returned in the result envelope, not persisted as a `.ai-team/` artifact by default — the orchestrator folds it directly into the Task Brief it composes next. Write it to disk only when a `report_destination` is injected.

## Decision Gates

| Condition | Action |
|---|---|
| `mode: bootstrap` AND `config.yaml` already exists | Return `status: blocked`. |
| `mode: bootstrap` AND `config.yaml` missing | Run Phase A stack detection → write `config.yaml` per [references/config-template.md](references/config-template.md). |
| `mode: discover` | Run Phase A/B scoped to `topic` → return a discovery report in the envelope. |
| `mode` missing, or `topic` absent in discover mode | Recover from user-facing prompt text if possible; else `status: needs_input`, `context_resolution: fallback`, flag in envelope. |
| Architecture signals conflict during bootstrap | Default to `ddd` if `domain/application/infrastructure/` appear in ≥2 feature folders; else `layered`; else `unknown`. See [references/edge-cases.md](references/edge-cases.md). |

## Execution Steps

### Phase A — Glob/grep (free, no token budget)

1. Read `_shared/context-protocol.md` (startup) and `_shared/persistence-contract.md` (write rules — loaded per common-rules Principle 5; this skill writes `.ai-team/config.yaml` only in bootstrap mode). Identify mode from injected context (`mode:`, `project_root`, plus `topic` in discover mode).
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
8. **Discover**: compose the discovery report — Key Files (path, role, `file:line` evidence), Patterns Observed (existing conventions the Task Brief should follow), Risks (grounded citations), Open Questions (claims with no resolvable evidence). Return it in the envelope's `discovery_report` field. When `report_destination` is injected, also write it there (create its parent directory if absent).
9. Return the envelope per Output Contract.

## Output Contract

- Bootstrap: writes `.ai-team/config.yaml`. `context_resolution: none`.
- Discover: writes nothing by default; writes the report at `report_destination` (resolved relative to `project_root`) only when one is injected. `context_resolution: self-loaded` (or `fallback`).

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
