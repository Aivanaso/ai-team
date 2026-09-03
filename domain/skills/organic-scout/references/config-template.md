# config.yaml Template

Annotated YAML template for `.ai-team/config.yaml`. Fill in values detected during bootstrap
mode.

> **Format**: every block below uses `<placeholder>` or `{placeholder}` syntax for values the
> scout fills in. Inline comments list common alternatives (e.g. `e.g. typescript | php | go
> | ...`). The template names no canonical stack — it adapts to whatever the target project
> uses.

> **Canonical key set**: the orchestrator's Config Refresh Check (Session Init in
> `_shared/orchestrator-protocol.md`) diffs existing project configs against this template's
> top-level keys and offers to append the missing ones. When adding a key here, give it a
> safe-absent default (every consumer keeps working when the key is missing) so pre-existing
> projects upgrade additively on their next session.

```yaml
project:
  name: "{detected from project manifest (package.json / composer.json / Cargo.toml / go.mod / pyproject.toml / Gemfile) or directory name}"
  type: "{app | library | monorepo}"

stack:
  languages:
    - name: "{language}"        # e.g. typescript | php | go | rust | python | ruby
      version: "{version}"
    # Repeat the block per detected language.
  frameworks:
    - name: "{framework}"       # e.g. react | next | vue | angular | svelte | astro | nestjs | symfony | laravel | django | flask | rails
      version: "{version}"
    # Repeat the block per detected framework. Omit the list entirely if no framework is detected.
  testing:
    - name: "{test runner}"     # e.g. vitest | jest | mocha | playwright | cypress | phpunit | pytest | rspec | go test
    # Repeat the block per detected test runner.
  styling:
    - name: "{styling}"         # e.g. tailwind | sass | css-modules | styled-components | plain-css | none
      version: "{version}"      # omit if not versioned
    # Repeat the block per detected styling tool.
  package_manager: "{pm}"       # Options: pnpm | yarn | bun | npm | composer | cargo | go | pip | poetry | bundler

conventions:
  # Extract from existing config files (lint config, formatter config, editor config, language strictness flags).
  # Each entry is a one-line constraint that downstream delegations must respect.
  - "{constraint}"
  # Common examples (replace with detected): "max line length 120", "no default exports", "snake_case file names", "PSR-4 autoloading", "Conventional Commits", "strict mode enabled".

commit_strategy: auto  # orchestrator's own commit-creation step: auto = commits at each objective's
                       # close without pausing; manual = presents the staged file set and waits for
                       # user confirmation before committing (orchestrator-protocol.md -> "Commit creation")

# strict_tdd: true
#   Optional, safe-absent default: false. The orchestrator appends the
#   STRICT TDD MODE directive to organic-implementer delegations only when three
#   conditions hold together: strict_tdd: true, test_commands.unit is declared
#   below, and the objective changes behavior in a testable artifact the
#   declared runner can exercise (never prose/docs/config/templates/skill
#   definitions). strict_tdd: true with test_commands.unit absent sends no
#   directive -- the orchestrator tells the user and records the gap in the
#   Brief File, never inventing a runner command. organic-implementer then
#   returns tdd_cycles evidence for each red -> green cycle
#   (red -> green -> triangulate -> refactor).

# test_commands:
#   unit: "{command}"       # e.g. "npm test" | "pytest" | "phpunit"
#   security: "{command}"   # e.g. "npm audit" | "composer audit"
#   Optional. `unit` is the strict_tdd test runner the orchestrator cites, also re-run by
#   organic-reviewer's verification lens when acceptance_checks don't already cover it.
#   `security` is the dependency auditor organic-security reads in code-audit mode; omit
#   if not configured.

# review_gates:
#   - name: "{gate-id}"      # e.g. coverage, migration-lint
#     command: "{command}"   # e.g. "npm run coverage -- --min 80"; exit 0 = pass. The threshold
#                             # lives inside the command / project config, not in this key.
#     blocking: true          # optional, default true
#   Optional, safe-absent. Objective review gates executed by organic-reviewer's verification
#   lens (SKILL.md Step 4) alongside the Task Brief's acceptance_checks re-run — exit code
#   only. A failing gate lands in `lenses.correctness.findings[]` citing this gate's own
#   declaration line — always a resolvable citation. Findings carry their own per-finding
#   `confidence`; the orchestrator's downstream triage is the filter, never a suppression rule
#   at the lens (see `_shared/result-envelope.md` → Review Receipt). A failing blocking gate
#   (blocking: true, or blocking absent) is a CRITICAL finding (verdict: review-blocked);
#   blocking: false is a MAJOR finding that documents but does not block. An unrunnable gate is
#   omitted from `verification` and noted in `risks` — never fabricated pass/fail. Calibration
#   (`_shared/evidence-protocol.md` -> Rule 7): whoever hand-adds a gate here first runs it
#   against a known-failing state (or a synthetic fixture) to confirm it CAN fail, and runs it
#   twice to rule out a cached green; a zero-work result (e.g. "0 files analyzed", "no tests
#   matched") is never accepted as a passing gate. See config/schema.yaml for the full field
#   reference.

# retro: on-signal
#   Optional, safe-absent default: on-signal. Read by the orchestrator when a task's Brief File
#   flips to `status: done` (orchestrator-protocol.md -> "Retro trigger"), to decide whether to
#   delegate organic-retro:
#     always     -> delegate organic-retro (mode: retro) unconditionally at task close
#     on-signal  -> delegate only when >=1 signal fired this task: any re-brief, an infra-death,
#                   a red blocking review_gates gate, or a single delegation reporting >300k
#                   tokens
#     off        -> never delegate organic-retro
#   Absent from config.yaml behaves exactly like an explicit on-signal.

structure:
  source: "src/"
  tests: "src/**/*.test.ts"
  components: "src/components/"
  # Detected from actual directory structure. Common variations:
  #   source: "src/" | "app/" | "lib/" | "packages/{name}/src/"
  #   tests:  "**/*.spec.ts" | "tests/" | "__tests__/"

architecture:
  style: "{detected style}"
  # Options: ddd | hexagonal | mvc | layered | modular | unknown
  layers:
    - name: "{layer}"
      path: "{path}"
    # ddd example:
    #   - name: domain      path: src/*/domain/
    #   - name: application path: src/*/application/
    #   - name: infrastructure path: src/*/infrastructure/
    # layered example:
    #   - name: controllers path: src/controllers/
    #   - name: services    path: src/services/
    #   - name: entities    path: src/entities/
  bounded_contexts:
    - name: "{context}"
      path: "{path}"
    # Empty list [] when project is not DDD/hexagonal or single-domain
  patterns:
    - "{pattern}"
    # Values: cqrs | repository-pattern | event-driven | event-sourcing |
    #         mediator | factory-pattern | role-based-access | saga
    # Empty list [] when no patterns detected

# model_overrides:
#   Optional, safe-absent (defaults live in _shared/orchestrator-protocol.md -> "Model
#   Routing"). Project-level override of the default model per delegated worker.
#   organic-reviewer: opus     # e.g. upgrade from the sonnet default
#   Worker names: organic-implementer | organic-reviewer | organic-security |
#   organic-scout | organic-retro.

# rules:
#   Optional, safe-absent. Free-text custom rules for AI agents, added by hand
#   (not written by scout bootstrap).
#   - "{rule}"
#   Examples: "Never use default exports", "Database queries go through repository pattern".
```

## Detection Heuristics Summary

### Stack markers (scan project root in order)

| File | Detects |
|------|---------|
| `package.json` | Node.js, framework (react/next/vue/angular/svelte/nestjs), package manager |
| `tsconfig.json` | TypeScript |
| `composer.json` | PHP, framework (symfony/laravel) |
| `go.mod` | Go |
| `Cargo.toml` | Rust |
| `pyproject.toml` / `requirements.txt` | Python |
| `Gemfile` | Ruby |
| `turbo.json` / `pnpm-workspace.yaml` / `lerna.json` | Monorepo tooling |
| `vitest.config.*` / `jest.config.*` | Testing framework |
| `tailwind.config.*` | Tailwind CSS |

### Package manager (lock file precedence)

| Lock file | Package manager |
|-----------|----------------|
| `pnpm-lock.yaml` | pnpm |
| `yarn.lock` | yarn |
| `bun.lockb` / `bun.lock` | bun |
| `package-lock.json` | npm |
| `composer.lock` | composer |

### Architecture style signals

| Directory pattern | Infers |
|-------------------|--------|
| `domain/`, `application/`, `infrastructure/` nested inside feature folders | `ddd` |
| Top-level `domain/`, `application/`, `infrastructure/`, `presentation/` | `hexagonal` |
| Flat `controllers/`, `services/`, `models/`, `views/` | `mvc` |
| Flat `controllers/`, `services/`, `entities/`, `repositories/` | `layered` |
| Feature folders with mixed concerns | `modular` |
| No clear pattern | `unknown` |

### Code patterns signals

| File naming pattern | Pattern |
|---------------------|---------|
| `*Command.{ts,php}` + `*Handler.{ts,php}` | `cqrs` |
| `*Query.{ts,php}` + `*QueryHandler.{ts,php}` | `cqrs` (read side) |
| `*Event.{ts,php}` + `*Listener.{ts,php}` | `event-driven` |
| `*Repository.{ts,php}` interface + impl in different layer | `repository-pattern` |
| `*Saga.{ts,php}` or `*Projection.{ts,php}` | `event-sourcing` |
| `@nestjs/cqrs` usage | `mediator` |
