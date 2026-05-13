# config.yaml Template

Annotated YAML template for `.ai-team/config.yaml`. Fill in values detected during bootstrap mode.

> **Format**: every block below uses `<placeholder>` or `{placeholder}` syntax for values the scout fills in. Inline comments list common alternatives (e.g. `e.g. typescript | php | go | ...`). The template names no canonical stack — it adapts to whatever the target project uses.

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
  # Each entry is a one-line constraint that downstream phases must respect.
  - "{constraint}"
  # Common examples (replace with detected): "max line length 120", "no default exports", "snake_case file names", "PSR-4 autoloading", "Conventional Commits", "strict mode enabled".

commit_strategy: auto  # commit strategy for work-unit-commits skill: auto | manual

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
