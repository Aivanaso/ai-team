# Evidence Protocol

> How sub-agents ground their claims in the actual project, not in generic framework knowledge.

## Purpose

The most common failure mode in delegated runs is **assuming generic framework behavior applies verbatim to this project**. The 4 bugs in the ECO-944 retrospective all shared this pattern: the run relied on "standard framework behavior" instead of validating the specific project configuration.

This protocol defines six hard rules that every sub-agent MUST follow when writing plans, code, or review reports.

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

**Output requirement:** tasks that touch an interface MUST include a sub-task explicitly named "Implementors sweep for <InterfaceName>" with the grep commands run and the resulting file list.

**Schema/contract fields — same principle, markdown form:** a change to a serialized contract structure (envelope field, receipt schema, config key) sweeps every site that renders that structure — SKILL.md Output Contract blocks, `references/*.md` exemplars, templates, envelope examples. The sweep is owned like any acceptance check: the brief (or the worker's own `check_results`) carries the grep as a runnable check, and the reviewer re-runs it in its verification section. **The sweep grep is always an executed row** — a `check_results` entry, a `verification[]` row, or an inline closure's `gate_results` entry (command + output digest) — never a sentence in `decisions_taken`, in the brief, or in the Brief File's Amendments; an asserted sweep is the recurrent failure (G4b-A retro: one new field, three passes to converge, "single root: incomplete sweep of the new field"). A correct schema beside a lagging exemplar teaches the pre-change shape to every reader who loads the example (organic-v2 retro: recurred across 4 phases).

## Rule 3 — Test Adequacy Before Declaring Apply Done

A sub-agent that generates integration tests MUST execute those specific integration tests before reporting `status: ok`. Unit-only execution is NOT sufficient when the same phase also produced integration tests.

Rationale: mocking a framework boundary (e.g., `MessageBusInterface` as a spy) makes the test green regardless of actual routing. Real smoke of the test you just wrote is the only way to catch:

- Mock/real divergence (the AsyncBus routing bug)
- Entity manager / ORM lifecycle errors (the `em->clear()` bug)
- Fatal errors in doubles that implement renamed interfaces

**Scope:** only the integration tests the phase itself created or modified — not the full suite. They are few and fast.

**Exception:** if the project's test infrastructure genuinely cannot run an integration test locally (e.g., requires external services not available in the sandbox), report it as a risk in the envelope rather than silently skipping (the orchestrator decides whether to defer or override).

## Rule 4 — Validate Assumed Invariants at Brief-Authoring / Discovery Time

When a Task Brief or a discovery report depends on a **codebase-wide invariant** (a naming convention, a regex, a contract, a "consistency" assumption), the party asserting it — the orchestrator composing the Task Brief, or `organic-scout` running discovery — MUST validate it with greps before finalizing the brief or the report. The `scope_proposal` block (`organic-scout`, discover mode) is this rule's natural artifact: an invariant the proposal relies on is validated — or listed as an open question — before the brief is composed.

**Trigger** — this rule activates ONLY if the brief's objective/out_of_scope text, the discovery request, or the user's request contains one of these signals about the invariant:

- "todos", "todas", "siempre", "nunca", "convención", "convention"
- "all", "every", "always", "never", "consistent", "uniform"
- A regex or pattern stated as currently true (e.g., "all `messageName()` return `<context>.<event>`")

If none of these appear, stay within the exploration budget declared in the delegation prompt (extra greps inflate context without improving accuracy) — the brief or report stays as-is.

**When triggered**:

1. Identify the invariant explicitly (one sentence: "the brief/report assumes X holds for all Y").
2. Run **at most 3-5 greps** that would surface counter-examples. Pick the cheapest first.
3. If counter-examples exist, report them as a `MAJOR` finding (canonical severity vocabulary — CRITICAL / MAJOR / MINOR, see `_shared/result-envelope.md` → Review Receipt) in the discovery report's `risks` (or the orchestrator's questions to the user before delegating), with the exact list (or "N occurrences, sample: ...") and two paths: (a) fix all counter-examples in scope, or (b) carve an allowlist.
4. If grep is clean, add a one-line note: `Invariant validated: <description> — N matches, 0 counter-examples (grep: <pattern>)`. This becomes evidence the Task Brief can cite.

**Bad (assumed):**
> "Add a routing test that asserts all `messageName()` follow `<context>.<event>`."

**Good (validated):**
> "Add a routing test for `messageName()` convention. Invariant check: 15 legacy events do NOT follow the convention (e.g., `BudgetCreated`, `ProposalSent`). MAJOR — user must decide allowlist vs migration before the brief is finalized."

**Why this exists**: in the messenger-buses retrospective, 15 legacy `messageName()` violations surfaced mid-implementation and forced a re-brief. They were greppable before delegation.

**Out of scope for this rule**: framework-behavior claims (Rule 1 covers them), interface-signature and schema/contract-field sweeps (Rule 2), test execution (Rule 3). Rule 4 is specifically about invariants the brief or report *itself* asserts as currently true.

## Rule 5 — Cross-Repo Pattern Transplant Check

When a Task Brief, discovery report, or review finding cites a pattern from a **sibling/sister repository** as evidence (not the current repo), the agent MUST verify that the pattern's structural prerequisites also hold in the target repo before recommending the transplant.

Rule 1 covers framework behavior in the current repo. This rule covers the gap: "we'll do it like `corev3` does" is NOT sufficient evidence — `corev3`'s pattern depends on `corev3`'s topology, which may not match.

**Trigger** — this rule activates when the agent writes one of these phrases (or their Spanish equivalents):

- "mirror of {repo}", "same pattern as {repo}", "replicate from {repo}", "como hace {repo}"
- A path that crosses repos (e.g., `../{other-repo}/...`, `~/Proyectos/{other-repo}/...`)
- An evidence citation pointing outside the current project root (the Task Brief's `target_repo`)

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

**Citation format** — embed in the Task Brief, result envelope, Review Receipt, or discovery report when a transplant is involved:

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

Sub-agent result envelopes are self-reports. The orchestrator MUST treat them as claims, not as proof, and run an independent verification before committing when the change is non-trivial.

This rule covers the orchestrator's responsibility *after* receiving an envelope. Rule 3 covers what `organic-implementer` must do *internally* before composing its envelope (test execution). Rule 6 covers what the orchestrator does on top.

**Trigger** — activate when ALL of:

- `organic-implementer` returned `status: ok` or `status: warning`
- The Task Brief's `expected_files` has >3 entries, OR crosses >1 module boundary, OR the brief's objective resolved an open scope question the user raised before delegating

**When triggered**, the orchestrator MUST cross-check three things (the operational hooks are the artifact-confirmation check in `orchestrator-protocol.md` → "Organic Delegation Route → What comes back" and the Citation audit in "Evidence-Tier Review"):

1. **Scope drift** — every file in `git diff --name-only` traces to the Task Brief's `expected_files` or the envelope's `artifacts`. A file that traces to neither is scope creep to flag.
2. **Objective coverage** — the Task Brief's objective and every item in `acceptance_checks` are actually addressed in the diff (grep by keyword/invariant). A check that passes without touching code plausibly related to it is a silent skip.
3. **Test discovery sanity** — if new test files were added, the global test count grew proportionally to the count of new files. Disk-present tests with a flat global counter indicate dormant tests (runner glob/discover misconfigured).

**Decision**:

- All three checks pass → proceed to Evidence-Tier Review / commit.
- Any check fails → re-engage `organic-implementer` with the gap list inlined per the mandatory `## Re-engage Reason` block (`orchestrator-protocol.md` → "Re-engage prompt block"); this re-delegation counts against the shared re-brief budget (DD-14).

**Why this exists**: in retrospective analysis of large multi-domain changes, implementers have returned `status: ok` while (a) silently skipping entire cross-cutting concerns, and (b) placing test files where the runner did not pick them up. `organic-implementer`'s own Decision Gates catch a missing acceptance check but cannot detect a runner-discovery failure or a resolution gap the checks themselves don't probe — those require the orchestrator's full-brief view. `organic-implementer` has no write authority over any audit trail; it surfaces scope gaps via a `paused` amendment request first, then via `scope_report` when the channel is exhausted or denied. The three cross-checks above remain the orchestrator's independent verification mechanism.

**Out of scope**: trivial single-file briefs (1 file, no cross-module scope, no resolved open question) — their evidence requirements are covered by Rules 1-3 alone.

## Rule 7 — Declared Checks Must Be Able to Fail

A check or gate declared in a Task Brief's `acceptance_checks`, an `organic-scout` `scope_proposal`'s `acceptance_checks`, or a `.ai-team/config.yaml` `review_gates`/`test_commands` entry MUST be calibrated against a known positive before its green counts as evidence — the pre-change state that should fail, or (when no pre-change failing state exists yet) a synthetic failing fixture built for exactly that purpose. A check that has never been observed to fail is not verified to test anything; it is only verified to run.

**Calibration checklist:**

1. **Run against a known failure first.** Before trusting a green result, confirm the same check fails against the pre-change state, or against a synthetic fixture built to trigger the failure the check exists to catch.
2. **Run twice to expose cache hits.** A test runner, linter, or static analyzer that reports green because it cached a prior (possibly stale) result looks identical to a green result from actually re-running the check — running twice in a row, and confirming both runs actually executed work, surfaces a silent cache hit that a single run cannot.
3. **Reject zero-work outputs as green.** `No files analyzed`, `No tests found`, `0 suites`, `0 findings checked`, and equivalent zero-work digests are never accepted as a passing result — they are indistinguishable from "the check never ran against real content". A zero-work result has exactly ONE disposition, canonical across every consumer of this rule: it DID execute, so it is recorded as `outcome: fail` in the verification/check-results evidence (fail closed — a fail contradicting a worker's claimed `pass` is then the existing discrepancy finding, which is the intended consequence), with the zero-work nature named in `risks`. Never omitted from the evidence, never recorded as `pass`, and never conflated with a check that genuinely could not be run at all (missing tool, unreachable command) — that distinct, separately-named failure mode is handled elsewhere in each consuming skill's own gates.

**Relationship to Rules 3 and 6:** Rule 3 requires `organic-implementer` to execute the integration tests it wrote before declaring `status: ok`; Rule 6 bullet 3 ("Test discovery sanity") gives the orchestrator's post-hoc symptom for the same failure class (a flat global test counter despite new test files on disk). Rule 7 generalizes both: it is not limited to test execution, and it applies at the moment a check is DECLARED (brief authoring, `scope_proposal` composition, `config.yaml` bootstrap or hand-edit) rather than only at the moment it is later re-run.

**Why this exists**: three separate repositories produced four checks that could report green without ever having the capacity to fail — a static analyzer accepting `No files analyzed` as a clean pass, a test command matching zero test files while reporting success, and a cached linter run reporting a stale green after the underlying rule was already broken (eco-1066 retro F2, inputbag retro F3, deep-link retro F2). A check nobody has watched fail is a check nobody has verified.

## Recording Evidence in Artifacts

When composing a Task Brief, a result envelope, a Review Receipt, or a discovery report:

- Inline citations are cheap: `messenger.yaml:75`, `RunWorkerAsyncCommand:42`
- Use footnote-style references for reused evidence
- Never write "Symfony works this way" or "Doctrine handles this" — always cite

## When Evidence Conflicts With the Task Brief

If the cited evidence contradicts the Task Brief or a prior discovery report, surface the conflict instead of silently reconciling. Example: if the brief assumes `toPrimitives()` is the project's serialization convention but the project's existing async pattern uses raw arrays, report it as a `risk` in the returned envelope (or a `question` under `status: needs_input` when it blocks progress) and let the orchestrator/user decide.
