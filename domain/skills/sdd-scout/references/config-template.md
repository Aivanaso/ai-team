# config.yaml Template

Annotated YAML template for `.ai-team/config.yaml`. Fill in detected values during bootstrap mode.

```yaml
project:
  name: "{detected from package.json name or directory name}"
  type: "{app | library | monorepo}"

stack:
  languages:
    - name: typescript
      version: "5.x"
    # Add: php, go, rust, python, ruby as detected
  frameworks:
    - name: react
      version: "19.x"
    - name: next
      version: "14.x"
    # Add any detected framework: nestjs, symfony, laravel, astro, vue, angular, svelte
  testing:
    - name: vitest
    # Add: jest, phpunit, playwright, pytest
  styling:
    - name: tailwind
      version: "4.x"
    # Add: sass, css-modules, styled-components
  package_manager: pnpm
  # Options: pnpm | yarn | bun | npm | composer | cargo | go

conventions:
  # Extracted from existing config files (tsconfig.json, eslint.config.*, .editorconfig)
  - "strict TypeScript (strict: true in tsconfig)"
  - "ESM modules"
  - "path aliases via @/"
  # Add detected conventions: "PSR-4 autoloading", "Conventional Commits", "E2E tests with Playwright", etc.

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
