# Evidence Protocol

> How sub-agents ground their claims in the actual project, not in generic framework knowledge.

## Purpose

The most common failure mode in delegated runs is **assuming generic framework behavior applies verbatim to this project**. The 4 bugs in the ECO-944 retrospective all shared this pattern: the run relied on "standard framework behavior" instead of validating the specific project configuration.

This protocol defines seven hard rules that every sub-agent MUST follow when writing plans, code, or review reports.

## Rule 1 — Framework / Library Behavior Claims

Any statement about how a framework, library, or runtime behaves in this project MUST be backed by **one of these two sources of evidence**:

- **Config citation** — a specific file and line from the project's config (`messenger.yaml:75`, `doctrine.yaml:12`, `services.yaml:42`, etc.)
- **Existing caller** — a concrete class/file in the project that demonstrates the behavior (`RunWorkerAsyncCommand`, `WriteDealFromCrm`, etc.)

**Bad (generic assumption):**
> "The CommandBus routes AsyncCommand to the async transport regardless of the bus used."

**Good (project-specific evidence):**
> "messenger.yaml:75 routes AsyncCommand → async_commands transport. BUT command.bus at messenger.yaml:22 overrides `middleware:` and removes `SendMessageMiddleware` → dispatch via CommandBus runs sync. Async dispatch requires AsyncBusInterface (see `RecalculateServiceBillingProposalController:45`)."

If evidence cannot be gathered (unfamiliar config, no existing caller), mark the claim as an assumption to validate and surface it as a risk in the envelope (silent guesses compound into cascading failures).

**Applies to:** routing, serialization, caching, transactions, events, middleware, dependency injection, autowiring, type coercion, ORM lifecycle.

## Rule 2 — Interface Signature and Contract-Field Changes Require an Implementors Sweep

When a change renames, modifies, or removes a method on a **public interface** (not private/protected) — or, per the schema/contract clause at the end of this rule, a field of a serialized contract structure:

1. Grep the old method name across `src/`, `tests/`, `config/`, and any custom directories
2. Enumerate implementors (`implements <InterfaceName>`) including test doubles, mocks, fakes, stubs
3. List every caller of the old name
4. Include all of them in the task scope — not just the "obvious" callers in `src/`

Test doubles in `tests/Double/`, `tests/Mock/`, `tests/Fixture/` are invisible to a `src/`-only scope and WILL cause fatal runtime errors when tests boot.

**Output requirement:** a phase that touches an interface carries a check or a `decisions_taken` entry named "Implementors sweep for <InterfaceName>" with the grep commands run and the resulting file list.

**Schema/contract fields — same principle, markdown form:** a change to a serialized contract structure (envelope field, receipt schema, config key) sweeps every site that renders that structure — SKILL.md Output Contract blocks, `references/*.md` exemplars, templates, envelope examples. The sweep is owned like any acceptance check: the phase (or the worker's own `check_results`) carries the grep as a runnable check, and the reviewer re-runs it in its verification section. **The sweep grep is always an executed row** — a `check_results` entry or a `verification[]` row (command + output digest) — never a sentence in `decisions_taken` or in the design; an asserted sweep is the recurrent failure (G4b-A retro: one new field, three passes to converge, "single root: incomplete sweep of the new field"). A correct schema beside a lagging exemplar teaches the pre-change shape to every reader who loads the example (organic-v2 retro: recurred across 4 phases).

## Rule 3 — Test Adequacy Before Declaring Apply Done

A sub-agent that generates integration tests MUST execute those specific integration tests before reporting `status: ok`. Unit-only execution is NOT sufficient when the same phase also produced integration tests.

Rationale: mocking a framework boundary (e.g., `MessageBusInterface` as a spy) makes the test green regardless of actual routing. Real smoke of the test you just wrote is the only way to catch:

- Mock/real divergence (the AsyncBus routing bug)
- Entity manager / ORM lifecycle errors (the `em->clear()` bug)
- Fatal errors in doubles that implement renamed interfaces

**Scope:** only the integration tests the phase itself created or modified — not the full suite. They are few and fast.

**Exception:** if the project's test infrastructure genuinely cannot run an integration test locally (e.g., requires external services not available in the sandbox), report it as a risk in the envelope rather than silently skipping (the orchestrator decides whether to defer or override).

Under the STRICT TDD MODE directive the same discipline covers each test's red run: a red is evidence only when it is a valid red per `organic-implementer`'s Output Contract (`tdd_cycles`) — Rule 7 item 3 applies to a red exactly as to a green.

## Rule 4 — Validate Assumed Invariants at Design / Scope Time

When a design, a scope report or a map report depends on a **codebase-wide invariant** (a naming convention, a regex, a contract, a "consistency" assumption), the party asserting it — the orchestrator writing the design with the user, or `organic-scout` in map or scope mode — MUST validate it with greps before finalizing the design or the report. The scope report is this rule's natural artifact: an invariant a phase relies on is validated — or listed in `open_questions` — before the plan is generated.

**Trigger** — this rule activates ONLY if the design's objective or out-of-scope text, the scout's topic, or the user's request contains one of these signals about the invariant:

- "todos", "todas", "siempre", "nunca", "convención", "convention"
- "all", "every", "always", "never", "consistent", "uniform"
- A regex or pattern stated as currently true (e.g., "all `messageName()` return `<context>.<event>`")

If none of these appear, stay within the exploration budget declared in the delegation prompt (extra greps inflate context without improving accuracy) — the design or report stays as-is.

**When triggered**:

1. Identify the invariant explicitly (one sentence: "the design/report assumes X holds for all Y").
2. Run **at most 3-5 greps** that would surface counter-examples. Pick the cheapest first.
3. If counter-examples exist, report them in the report's `risks` (or as the orchestrator's question to the user before approval), with the exact list (or "N occurrences, sample: ...") and two paths: (a) fix all counter-examples in scope, or (b) carve an allowlist — the user decides in the design.
4. If grep is clean, add a one-line note: `Invariant validated: <description> — N matches, 0 counter-examples (grep: <pattern>)`. This becomes evidence the design can cite.

**Bad (assumed):**
> "Add a routing test that asserts all `messageName()` follow `<context>.<event>`."

**Good (validated):**
> "Add a routing test for `messageName()` convention. Invariant check: 15 legacy events do NOT follow the convention (e.g., `BudgetCreated`, `ProposalSent`). MAJOR — user must decide allowlist vs migration before the design is approved."

**Why this exists**: in the messenger-buses retrospective, 15 legacy `messageName()` violations surfaced mid-implementation and forced a second attempt. They were greppable before delegation.

**Out of scope for this rule**: framework-behavior claims (Rule 1 covers them), interface-signature and schema/contract-field sweeps (Rule 2), test execution (Rule 3). Rule 4 is specifically about invariants the design or report *itself* asserts as currently true.

## Rule 5 — Cross-Repo Pattern Transplant Check

When a design, scout report, or review finding cites a pattern from a **sibling/sister repository** as evidence (not the current repo), the agent MUST verify that the pattern's structural prerequisites also hold in the target repo before recommending the transplant.

Rule 1 covers framework behavior in the current repo. This rule covers the gap: "we'll do it like `corev3` does" is NOT sufficient evidence — `corev3`'s pattern depends on `corev3`'s topology, which may not match.

**Trigger** — this rule activates when the agent writes one of these phrases (or their Spanish equivalents):

- "mirror of {repo}", "same pattern as {repo}", "replicate from {repo}", "como hace {repo}"
- A path that crosses repos (e.g., `../{other-repo}/...`, `~/Proyectos/{other-repo}/...`)
- An evidence citation pointing outside the current project root

If none of these appear, the artifact stays as-is (skip the check — running it outside this trigger inflates context without benefit).

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

**Citation format** — embed in the design, result envelope, Review Receipt, or scout report when a transplant is involved:

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

Sub-agent result envelopes are self-reports. The orchestrator treats them as claims: it
confirms every `artifacts` path exists under the project root and that `git status` shows only
the phase's files before settling a ticket, and the reviewer re-runs every declared check
rather than trusting the implementer's `check_results` (a contradiction is a CRITICAL
finding). The orchestrator's side of this rule lives in `_shared/cards/ingest.md`; the
reviewer's side in `organic-reviewer/SKILL.md` → Hard Rules. Rule 3 covers what the
implementer must do *internally* before composing its envelope; this rule covers what happens
to that envelope afterwards.

## Rule 7 — Declared Checks Must Be Able to Fail

A check declared in a design phase's `Check:` line, an `organic-scout` scope report's `acceptance_checks`, a generated phase file, or a `.ai-team/config.yaml` `review_gates`/`test_commands` entry MUST be calibrated against a known positive before its green counts as evidence — the pre-change state that should fail, or (when no pre-change failing state exists yet) a synthetic failing fixture built for exactly that purpose. A check that has never been observed to fail is not verified to test anything; it is only verified to run.

**Calibration checklist:**

1. **Run against a known failure first.** Before trusting a green result, confirm the same check fails against the pre-change state, or against a synthetic fixture built to trigger the failure the check exists to catch.
2. **Run twice to expose cache hits.** A test runner, linter, or static analyzer that reports green because it cached a prior (possibly stale) result looks identical to a green result from actually re-running the check — running twice in a row, and confirming both runs actually executed work, surfaces a silent cache hit that a single run cannot.
3. **Reject zero-work outputs as green.** `No files analyzed`, `No tests found`, `0 suites`, `0 findings checked`, and equivalent zero-work digests are never accepted as a passing result — they are indistinguishable from "the check never ran against real content". A zero-work result has exactly ONE disposition, canonical across every consumer of this rule: it DID execute, so it is recorded as `outcome: fail` in the verification/check-results evidence (fail closed — a fail contradicting a worker's claimed `pass` is then the existing discrepancy finding, which is the intended consequence), with the zero-work nature named in `risks`. Never omitted from the evidence, never recorded as `pass`, and never conflated with a check that genuinely could not be run at all (missing tool, unreachable command) — that distinct, separately-named failure mode is handled elsewhere in each consuming skill's own gates.

**Relationship to Rules 3 and 6:** Rule 3 requires `organic-implementer` to execute the integration tests it wrote before declaring `status: ok`; Rule 6 makes the reviewer re-run them. Rule 7 generalizes both: it is not limited to test execution, and it applies at the moment a check is DECLARED (the design's `Check:` line, the scope report, `config.yaml` bootstrap or hand-edit) rather than only at the moment it is later re-run.

**Why this exists**: three separate repositories produced four checks that could report green without ever having the capacity to fail — a static analyzer accepting `No files analyzed` as a clean pass, a test command matching zero test files while reporting success, and a cached linter run reporting a stale green after the underlying rule was already broken (eco-1066 retro F2, inputbag retro F3, deep-link retro F2). A check nobody has watched fail is a check nobody has verified.

## Recording Evidence in Artifacts

When composing a design, a result envelope, a Review Receipt, or a scout report:

- Inline citations are cheap: `messenger.yaml:75`, `RunWorkerAsyncCommand:42`
- Use footnote-style references for reused evidence
- Never write "Symfony works this way" or "Doctrine handles this" — always cite

## When Evidence Conflicts With the Phase

If the cited evidence contradicts the phase file, the design or a prior scout report, surface the conflict instead of silently reconciling. Example: if the design assumes `toPrimitives()` is the project's serialization convention but the project's existing async pattern uses raw arrays, report it as a `risk` in the returned envelope (or a `question` under `status: needs_input` when it blocks progress) and let the orchestrator/user decide.
