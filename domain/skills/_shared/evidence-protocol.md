# Evidence Protocol

> How sub-agents ground their claims in the actual project, not in generic framework knowledge.

## Purpose

The most common failure mode in SDD runs is **assuming generic framework behavior applies verbatim to this project**. The 4 bugs in the ECO-944 retrospective all shared this pattern: design/tasks/apply relied on "standard framework behavior" instead of validating the specific project configuration.

This protocol defines six hard rules that every sub-agent MUST follow when writing specs, designs, tasks, code, or verification reports.

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

## Rule 5 — Cross-Repo Pattern Transplant Check

When propose, design, or tasks cite a pattern from a **sibling/sister repository** as evidence (not the current repo), the agent MUST verify that the pattern's structural prerequisites also hold in the target repo before recommending the transplant.

Rule 1 covers framework behavior in the current repo. This rule covers the gap: "we'll do it like `corev3` does" is NOT sufficient evidence — `corev3`'s pattern depends on `corev3`'s topology, which may not match.

**Trigger** — this rule activates when the agent writes one of these phrases (or their Spanish equivalents):

- "mirror of {repo}", "same pattern as {repo}", "replicate from {repo}", "como hace {repo}"
- A path that crosses repos (e.g., `../{other-repo}/...`, `~/Proyectos/{other-repo}/...`)
- An evidence citation pointing outside the current `change_dir` / project root

If none of these appear, do NOT run the check — the proposal/design/tasks stays as-is.

**When triggered**, the agent MUST:

1. **Identify the source pattern** — name the source repo, file, and a 1-line summary of the pattern.
2. **Identify the target equivalent** — the file in the current repo where the pattern would land. If no equivalent exists, that itself is a precondition gap to escalate.
3. **Enumerate structural prerequisites** of the source pattern across the relevant axes (pick only those that apply to the pattern):

   | Axis | Question to answer |
   |------|---------------------|
   | Build topology | multi-stage vs single-stage; what gets copied in each stage |
   | Dependency layout | where `composer.json` / `package.json` lives relative to the pattern |
   | Framework version | the version + minor; whether the cited behavior exists in the target's version |
   | Runtime topology | shared network / volumes / DNS namespace with other services |
   | Environment scope | does the pattern run identically in local / CI / PRE / PRO |

4. **Verify each axis** in the target repo with a `grep` or `read` of the equivalent file.
5. **Decide**:
   - `proceed` — all relevant axes match.
   - `adapt` — minor mismatch, document the adaptation inline.
   - `reject` — at least one axis breaks the pattern's assumption; escalate to user with the failing axis named.

**Citation format** — embed in design.md / proposal.md / tasks.md when a transplant is involved:

```
Pattern transplant: {one-line description}
  Source: {origin-repo}/{file}:{line}
  Target: {target-repo}/{equivalent-file}:{line}   # or "(does not exist yet)"
  Precondition checks:
    - {axis}: source={X}, target={Y}, match=Y/N
    - {axis}: source={X}, target={Y}, match=Y/N
  Decision: {proceed | adapt | reject}
  {if adapt or reject: 1-line reason}
```

**Bad (assumed):**
> "Mirror of corev3's `1-build-php.sh` — pull-first-or-build pattern."

**Good (validated):**
> ```
> Pattern transplant: pull-first-or-build CI pattern
>   Source: corev3/scripts/1-build-php.sh:42
>   Target: cuideo-core/scripts/build-php.sh (does not exist yet)
>   Precondition checks:
>     - Build topology: source=multi-stage (base = PHP+ext only),
>                       target=single-stage (base copies composer.json + src/),
>                       match=N
>   Decision: REJECT — single-stage base is commit-dependent;
>             pull-first would serve stale composer.lock.
> ```

**Why this exists**: in the ECO-971 retrospective, three failures (T1.5 cache miss, `auto_setup` misread, DNS shadowing) all stemmed from transplanting a corev3 pattern without checking that cuideo-core had the same structural prerequisites.

**Out of scope for this rule**: claims about the framework that ARE backed by the current repo's config (Rule 1 covers those); patterns invented from scratch (no transplant happening); patterns cited from generic docs/blog posts (cite the docs as evidence per Rule 1 instead).

## Rule 6 — Sub-Agent Envelope Is a Declaration, Not a Verification

Sub-agent result envelopes are self-reports. The orchestrator MUST treat them as claims, not as proof, and run an independent verification before delegating to the next phase when the change is non-trivial.

This rule covers the orchestrator's responsibility *after* receiving an envelope. Rule 3 covers what apply must do *internally* before composing its envelope (test execution). Rule 6 covers what the orchestrator does on top.

**Trigger** — activate when ALL of:

- The phase is `apply` or `verify`
- The change has >3 tasks, OR >1 affected domain, OR any open question / cross-cutting decision was resolved
- The envelope returned `status: ok` or `status: warning`

**When triggered**, the orchestrator MUST cross-check four things (operational details in `sdd-orchestrator-protocol.md → Post-Apply Independent Audit`):

1. **Scope drift** — every file in `git diff --name-only` traces to a `tasks.md` `Files:` block or a `decisions[]` entry. Unaccounted files = scope creep to flag.
2. **Resolution coverage** — every open question, design decision, and cross-cutting requirement recorded in the spec/design appears in the diff (grep by keyword/invariant). A resolution that does not surface anywhere is a silent skip.
3. **Audit trail completeness** — every commit outside the original task plan has a corresponding `decisions[]` entry with the matching phase. Zero `decisions[]` for a phase that visibly drifted = broken audit trail.
4. **Test discovery sanity** — if new test files were added, the global test count grew proportionally to the count of new files. Disk-present tests with a flat global counter indicate dormant tests (runner glob/discover misconfigured).

**Decision**:

- All four checks pass → advance to the next phase.
- Any check fails → re-engage the same phase sub-agent with an enumerated gap list (1/N…N/N). Log a `decisions[]` entry with `task_ref: post-{phase}-audit-gap` describing what was missing.

**Why this exists**: in retrospective analysis of large multi-domain SDDs, apply sub-agents have returned `status: ok` while (a) silently skipping entire cross-cutting concerns, (b) failing to log mid-flight decisions, and (c) placing test files where the runner did not pick them up. The on-disk deliverables audit inside `sdd-apply` (Step 7) catches missing files but cannot detect resolution gaps or runner-discovery failures — those require the orchestrator's full-plan view.

**Out of scope**: trivial single-task applies (1 file, no OQs, no decisions); the propose / spec / design phases — their evidence requirements are covered by Rules 1, 4, 5.

## Recording Evidence in Artifacts

When writing design.md, tasks.md, or verification-report.md:

- Inline citations are cheap: `messenger.yaml:75`, `RunWorkerAsyncCommand:42`
- Use footnote-style references for reused evidence
- Never write "Symfony works this way" or "Doctrine handles this" — always cite

## When Evidence Conflicts With Specs

If the cited evidence contradicts the spec or design input, surface the conflict instead of silently reconciling. Example: if the spec says "use toPrimitives()" but the project's existing async pattern uses raw arrays, report it as a Discovered Warning (`DW-N`) and let the user decide.
