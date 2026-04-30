# Evidence Protocol

> How sub-agents ground their claims in the actual project, not in generic framework knowledge.

## Purpose

The most common failure mode in SDD runs is **assuming generic framework behavior applies verbatim to this project**. The 4 bugs in the ECO-944 retrospective all shared this pattern: design/tasks/apply relied on "standard framework behavior" instead of validating the specific project configuration.

This protocol defines three hard rules that every sub-agent MUST follow when writing specs, designs, tasks, code, or verification reports.

## Rule 1 — Framework / Library Behavior Claims

Any statement about how a framework, library, or runtime behaves in this project MUST be backed by **one of these two sources of evidence**:

- **Config citation** — a specific file and line from the project's config (`messenger.yaml:75`, `doctrine.yaml:12`, `services.yaml:42`, etc.)
- **Existing caller** — a concrete class/file in the project that demonstrates the behavior (`RunWorkerAsyncCommand`, `WriteDealFromCrm`, etc.)

**Bad (generic assumption):**
> "The CommandBus routes AsyncCommand to the async transport regardless of the bus used."

**Good (project-specific evidence):**
> "messenger.yaml:75 routes AsyncCommand → async_commands transport. BUT command.bus at messenger.yaml:22 overrides `middleware:` and removes `SendMessageMiddleware` → dispatch via CommandBus runs sync. Async dispatch requires AsyncBusInterface (see `RecalculateServiceBillingProposalController:45`)."

If evidence cannot be gathered (unfamiliar config, no existing caller), **mark the claim as an assumption to validate** and surface it as a risk in the envelope. Do NOT silently propagate a guess.

**Applies to:** routing, serialization, caching, transactions, events, middleware, dependency injection, autowiring, type coercion, ORM lifecycle.

## Rule 2 — Interface Signature Changes Require an Implementors Sweep

When a change renames, modifies, or removes a method on a **public interface** (not private/protected):

1. Grep the old method name across `src/`, `tests/`, `config/`, and any custom directories
2. Enumerate implementors (`implements <InterfaceName>`) including test doubles, mocks, fakes, stubs
3. List every caller of the old name
4. Include all of them in the task scope — not just the "obvious" callers in `src/`

Test doubles in `tests/Double/`, `tests/Mock/`, `tests/Fixture/` are invisible to a `src/`-only scope and WILL cause fatal runtime errors when tests boot.

**Output requirement:** tasks that touch an interface MUST include a sub-task explicitly named "Implementors sweep for <InterfaceName>" with the grep commands run and the resulting file list.

## Rule 3 — Test Adequacy Before Declaring Apply Done

A sub-agent that generates integration tests MUST execute those specific integration tests before reporting `status: ok`. Unit-only execution is NOT sufficient when the same phase also produced integration tests.

Rationale: mocking a framework boundary (e.g., `MessageBusInterface` as a spy) makes the test green regardless of actual routing. Real smoke of the test you just wrote is the only way to catch:

- Mock/real divergence (the AsyncBus routing bug)
- Entity manager / ORM lifecycle errors (the `em->clear()` bug)
- Fatal errors in doubles that implement renamed interfaces

**Scope:** only the integration tests the phase itself created or modified — not the full suite. They are few and fast.

**Exception:** if the project's test infrastructure genuinely cannot run an integration test locally (e.g., requires external services not available in the sandbox), report it as a risk in the envelope rather than silently skipping.

## Rule 4 — Validate Assumed Invariants in Propose Phase

When a proposal depends on a **codebase-wide invariant** (a naming convention, a regex, a contract, a "consistency" assumption), the propose agent MUST validate it with greps before declaring the proposal ready.

**Trigger** — this rule activates ONLY if the proposal text or the user request contains one of these signals about the invariant:

- "todos", "todas", "siempre", "nunca", "convención", "convention"
- "all", "every", "always", "never", "consistent", "uniform"
- A regex or pattern stated as currently true (e.g., "all `messageName()` return `<context>.<event>`")

If none of these appear, do NOT run extra greps — propose stays as-is.

**When triggered**:

1. Identify the invariant explicitly (one sentence: "the proposal assumes X holds for all Y").
2. Run **at most 3-5 greps** that would surface counter-examples. Pick the cheapest first.
3. If counter-examples exist, list them in the **Risks** table as `severity: high` with the exact list (or "N occurrences, sample: ...") and propose two paths in **Open Questions**: (a) fix all counter-examples in scope, or (b) carve an allowlist.
4. If grep is clean, add a one-line note in the proposal: `Invariant validated: <description> — N matches, 0 counter-examples (grep: <pattern>)`. This becomes evidence for downstream phases.

**Bad (assumed):**
> "Add a routing test that asserts all `messageName()` follow `<context>.<event>`."

**Good (validated):**
> "Add a routing test for `messageName()` convention. Invariant check: 15 legacy events do NOT follow the convention (e.g., `BudgetCreated`, `ProposalSent`). See Risks R-2 — user must decide allowlist vs migration."

**Why this exists**: in the messenger-buses retrospective, 15 legacy `messageName()` violations surfaced in the apply phase (group 1) and forced mid-pipeline re-decisions. They were greppable in propose.

**Out of scope for this rule**: framework-behavior claims (Rule 1 covers them), interface signature sweeps (Rule 2), test execution (Rule 3). Rule 4 is specifically about invariants the proposal *itself* asserts as currently true.

## Recording Evidence in Artifacts

When writing design.md, tasks.md, or verification-report.md:

- Inline citations are cheap: `messenger.yaml:75`, `RunWorkerAsyncCommand:42`
- Use footnote-style references for reused evidence
- Never write "Symfony works this way" or "Doctrine handles this" — always cite

## When Evidence Conflicts With Specs

If the cited evidence contradicts the spec or design input, surface the conflict instead of silently reconciling. Example: if the spec says "use toPrimitives()" but the project's existing async pattern uses raw arrays, report it as a Discovered Warning (`DW-N`) and let the user decide.
