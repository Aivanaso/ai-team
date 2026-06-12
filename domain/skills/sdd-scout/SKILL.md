---
name: sdd-scout
description: "Trigger: orchestrator launches scout for bootstrap (no config.yaml), baseline (missing domain spec), or explore (open-ended investigation)."
disable-model-invocation: true
user-invocable: false
---

## Activation Contract

Run when the orchestrator launches scout at the start of a new SDD change or on demand. Three modes: **bootstrap** detects the project stack and generates `config.yaml`; **baseline** reverse-engineers a domain spec from existing code; **explore** investigates an open-ended topic and writes `findings.md`. Never write application code. Never modify existing source files.

## Hard Rules

- Follows common rules: read-only on app code, write-scope, envelope-always, seniority — see `_shared/common-rules.md`.
- Bootstrap: preserve existing `config.yaml` — return `status: blocked` if it already exists (user customizations accumulated across prior SDDs must not be lost). -- because overwriting destroys user customizations (test runner paths, language versions, project conventions) accumulated across prior SDDs.
- Baseline: document what the code **actually does**, not what you think it should. -- because aspirational specs ("what the code should do") create false baselines that every subsequent SDD inherits as if they were true.
- Bootstrap writes a `commit_strategy: auto` field at the root of generated `config.yaml`. Existing configs without the field are valid (backward-compatible default).
- Config evolution for existing projects is owned exclusively by the orchestrator's Config Refresh Check (Auto-Init: additive key diff against `references/config-template.md`); scout writes `config.yaml` only on first bootstrap. -- because a single additive owner keeps user customizations safe — two writers of the same file with different merge semantics would race.

## Decision Gates

| Condition | Action |
|---|---|
| `mode: bootstrap` AND `config.yaml` already exists | Return `status: blocked`. |
| `mode: bootstrap` AND `config.yaml` missing | Run Phase A stack detection → write `config.yaml` per [references/config-template.md](references/config-template.md). |
| `mode: baseline` | Run Phase A/B scoped to domain → write base spec to `.ai-team/specs/{domain}/spec.md`. |
| `mode: explore` | Run Phase A/B scoped to topic → write `.ai-team/explorations/{topic}/findings.md`. |
| Context field missing for mode (e.g. `topic` absent in explore) | Recover from user-facing prompt text; set `context_resolution: fallback`; flag in envelope. |
| Architecture signals conflict during bootstrap | Default to `ddd` if `domain/application/infrastructure/` appear in ≥2 feature folders; else `layered`; else `unknown`. See [references/edge-cases.md](references/edge-cases.md). |

## Execution Steps

### Phase A — Glob/grep (free, no token budget)

1. Read shared context per `_shared/context-protocol.md`.
2. Identify mode from injected context block (`mode:`, `project_root`, plus `domain` / `topic` if applicable).
3. Glob project root for stack markers: `package.json`, `composer.json`, `go.mod`, `Cargo.toml`, `pyproject.toml`, `Gemfile`, `turbo.json`, `pnpm-workspace.yaml`, `lerna.json`. Detect language, framework, package manager, monorepo status from these files without reading them fully (names suffice for first pass).
4. Grep for architecture signals: directory names `domain/`, `application/`, `infrastructure/`, `controllers/`, `services/`, `entities/` under `src/`. Grep for code patterns: `*Command.ts`, `*Handler.ts`, `*Event.ts`, `*Repository.ts`, `*Saga.ts`.
5. For baseline/explore: grep for domain/topic keywords to locate relevant files (controllers, services, entities, DTOs, test files, pages/components).

### Phase B — Selective reads (budgeted, max 15 files)

6. **Bootstrap**: read `package.json` (if Node.js) for `name`, `workspaces`, framework deps. Read `tsconfig.json` for `strict`, path aliases. Scan top 2 levels of `src/` directory tree.
7. **Baseline**: read all source files for the domain (entity, services, controller, DTOs, migrations, tests). Reverse-engineer requirements from entity fields/constraints, controller endpoints, service methods, guards, validation rules, and tests.
8. **Explore**: read the 15 most relevant files (ranked by keyword match density). Analyze patterns and how the topic is currently implemented.

### Write artifacts

9. **Bootstrap**: generate `.ai-team/config.yaml` using [references/config-template.md](references/config-template.md). In addition to existing fields, write `commit_strategy: auto` at the root level of `config.yaml`. This is mandatory for new bootstraps (REQ-SCOUT-015). Language detection heuristics:
   - Monorepo: `turbo.json` OR `pnpm-workspace.yaml` OR `lerna.json` OR `workspaces` field in `package.json` OR multiple package manifests in direct child dirs.
   - App vs library: `main.ts`/routes/controllers → `app`; `package.json` with `main`/`exports`/`types` and no server code → `library`.
   - Package manager lock file precedence: `pnpm-lock.yaml` > `yarn.lock` > `bun.lockb` > `package-lock.json` > `composer.lock`.
   - Dispatch: bootstrap → write config.yaml. baseline → write spec.md. explore → write findings.md.
10. **Baseline**: write `.ai-team/specs/{domain}/spec.md`. Cross-domain ownership rule: business logic lives with the entity owner; authorization lives with the actor; never duplicate full scenarios in both specs. Frontend granularity: one REQ per domain (not per page); pages become scenarios within that REQ.
11. **Explore**: write `.ai-team/explorations/{topic}/findings.md` with Summary, Current Implementation, Key Files table, Patterns Observed, Architecture, Recommendations, Open Questions.
12. Update `state.yaml` per `_shared/persistence-contract.md`. Return envelope per [references/envelope-examples.md](references/envelope-examples.md).

## Output Contract

- Bootstrap: `.ai-team/config.yaml`. `context_resolution: none`.
- Baseline: `.ai-team/specs/{domain}/spec.md`. `context_resolution: injected` (or `fallback`).
- Explore: `.ai-team/explorations/{topic}/findings.md`. `context_resolution: injected` (or `fallback`).
- All envelopes: `status`, `executive_summary`, `artifacts`, `next_recommended`, `model_used`, `context_resolution`.

## References

- [references/config-template.md](references/config-template.md) — annotated config.yaml template; load during bootstrap when generating config.
- [references/envelope-examples.md](references/envelope-examples.md) — envelope variants per mode; load when building the result envelope.
- [references/edge-cases.md](references/edge-cases.md) — monorepo multi-stack, ambiguous architecture, config.yaml exists, no language detected; load when encountering non-happy-path conditions.
- `../_shared/context-protocol.md` — startup sequence.
- `../_shared/persistence-contract.md` — write rules.
- `../_shared/common-rules.md` — consolidated principles (read-only, write-scope, envelope-always, seniority); load at startup.
- `../_shared/result-envelope.md` — envelope schema.
- `../_shared/evidence-protocol.md` — Rules 1-5.
- `../_shared/spec-convention.md` — spec format (baseline mode).
