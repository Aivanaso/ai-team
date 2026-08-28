# Result Envelope

> Structured return format for all sub-agent responses.

## Purpose

Every sub-agent MUST return results in this format. The orchestrator ingests ONLY the envelope — it never reads full artifact contents. This keeps the orchestrator's context lean and focused on coordination.

## Format

```yaml
status: ok | warning | needs_input | blocked | failed  # + paused, intermediate only — see "Intermediate envelope — paused"
executive_summary: "1-3 sentence summary of what was done and key findings"
artifacts:
  - name: "endpoint"
    path: "services/billing/export.py"
  - name: "config"
    path: ".ai-team/config.yaml"
next_recommended:
  - "run the acceptance checks again after the next dependent change"
risks:
  - "Optional: any concerns or blockers discovered"
```

## Field Reference

### `status` (REQUIRED)

| Value | Meaning | Orchestrator action |
|-------|---------|-------------------|
| `ok` | Task completed successfully | Proceed to next phase |
| `warning` | Completed but with concerns | Show risks to user, proceed with caution |
| `needs_input` | Cannot proceed — user input is too vague or incomplete | Show questions to user, re-run agent with clarified input |
| `blocked` | Cannot proceed — missing dependency or technical blocker | Ask user for resolution |
| `failed` | Unrecoverable error | Report to user, suggest retry or alternative |

These five are the only **terminal** values — every skill execution resolves to exactly one of
them. One additional, non-terminal value, `paused`, exists solely for the scope-amendment
channel a skill's own contract may authorize — see "Intermediate envelope — paused" below.

### `executive_summary` (REQUIRED)

- 1-3 sentences maximum
- Written for the orchestrator, not the user (technical, precise)
- MUST include the key outcome — what changed, what was decided
- Example: `"Detected React 19 + TypeScript + Vitest stack. Generated config.yaml with 3 custom rules from existing ESLint config. No SKILL.md files found in project."`

### `artifacts` (REQUIRED, may be empty)

- List of files created or modified during the task
- Each entry has `name` (human-readable identifier) and `path` (relative to project root)
- Empty array `[]` is valid (e.g., for pure exploration tasks that only return a summary)

### `next_recommended` (REQUIRED, may be empty)

- Suggested next actions (e.g., "re-run this check after the dependent change lands")
- The orchestrator uses this as a hint, not a command
- Free-text, one line per suggestion — this route has no fixed phase vocabulary to reference

### `questions` (OPTIONAL)

- List of specific questions the agent needs answered before it can proceed
- Used with `status: needs_input` — the orchestrator surfaces these to the user
- Each question should be concrete and actionable, not generic
- Omit entirely if there are no questions

### `risks` (OPTIONAL)

- List of concerns, blockers, or technical debt discovered
- Orchestrator surfaces these to the user when relevant
- Omit entirely if there are no risks

### `model_used` (REQUIRED)

- The model alias this sub-agent ran on (e.g., `"sonnet"`, `"opus"`, `"haiku"`)
- Passed by the orchestrator in the prompt — report it back for traceability

### `context_resolution` (REQUIRED)

Compaction canary. Every sub-agent MUST report whether it received its expected context inputs from the orchestrator's delegation prompt, or had to recover them by itself.

Each SKILL.md declares an "Expected Context (injected by orchestrator)" list. At launch, the sub-agent checks whether all those inputs arrived in the prompt:

| Value | Meaning | What it tells the orchestrator |
|-------|---------|-------------------------------|
| `self-loaded` | Injected Context YAML received; SKILL.md and shared protocols read from disk per References section | Healthy — disk-read delegation worked correctly |
| `injected` | All expected context inputs were present in the prompt (legacy — when orchestrator inlined SKILL.md + protocols) | Healthy — backward-compatible with inline delegation |
| `fallback` | One or more expected inputs were missing; the sub-agent recovered them from other injected fields or by reading the target repo directly | Cache miss — orchestrator likely lost state (compaction). Re-derive the flag cache and re-inject in subsequent delegations |
| `none` | No expected inputs declared for this phase, or the sub-agent had nothing to verify | No signal — phase is context-light (e.g., scout bootstrap) |

The orchestrator inspects this field on every return. See `orchestrator-protocol.md` → "Context Resolution Feedback" for the self-correction rule.

**Rule for sub-agents**: do not lie. If you read a path that the orchestrator should have given you, report `fallback` and list which inputs were missing in `risks`. Silent fallback defeats the canary.

### `skill_resolution` (REQUIRED for `organic-implementer`)

Skill-injection canary for the one worker that consumes stack skills. The orchestrator forwards matching SKILL.md paths from `.ai-team/skill-registry.md` as a `## Skills to load before work` block to `organic-implementer` only (Critical Context Forwarding, `orchestrator-protocol.md`); this field reports what actually happened:

| Value | Meaning |
|-------|---------|
| `paths-injected` | Block received; every listed SKILL.md was read in full before writing |
| `path-missing` | Block received but ≥1 listed path is absent on disk — continued without it; missing paths listed in `risks` |
| `none` | No skills block in the prompt — proceeded on `config.yaml` conventions alone |

The orchestrator inspects this field on every return that carries it. See `orchestrator-protocol.md` → "Skill Resolution Feedback".

`organic-implementer` defines its own **bounded** envelope variant (Output Contract in its own
SKILL.md) rather than reusing this base schema verbatim — bounded evidence (`check_results`,
capped digests) instead of a raw-stdout evidence field, `scope_report` instead of a
structured deviation block, and `decisions_taken` (CAP 5, terminal envelopes only) for
behavioral decisions the brief did not fix. See that skill's Output Contract for its complete
field set.

## Intermediate envelope — paused

Terminal statuses (`ok | warning | needs_input | blocked | failed`) are unchanged and remain
terminal — every skill execution still resolves to exactly one of those five. A worker whose own
skill contract authorizes it — currently only `organic-implementer` — may additionally emit ONE
intermediate envelope kind, `status: paused`, when a scope gap surfaces mid-execution: not a
sixth terminal value, but a request that keeps the delegation open for one orchestrator
continuation message.

```yaml
status: paused                       # not terminal — the worker is waiting for one orchestrator continuation message
artifacts:                           # REQUIRED — files already written before pausing (Execution Steps implement before the pause gate, so partial writes are certain, not merely possible) — CAP 25 entries, same shape/cap discipline as the terminal artifacts field
  - { name: "<short label>", path: "<repo-relative path>" }
artifacts_omitted: 0                 # >0 only when the cap was hit
# decisions_taken does NOT travel here — it is terminal-only (organic-implementer's Output Contract); a pause carries the fields declared in this block and nothing more.
amendment_request:
  kind: scope-amendment
  reason: "<one sentence — which brief element the evidence outgrew>"
  evidence: "<path:line / command + output digest that proves the gap>"
  proposed_expected_files:           # CAP 10 entries — same shape/cap discipline as scope_report.needed_files — never a protected-class path, see denylist below
    - { action: CREATE|MODIFY|REMOVE, path: "<repo-relative path>", evidence: "<path:line — why>" }
  proposed_checks: []                # optional, same shape as acceptance_checks — each entry carries verified: "<how runnability was proven>" (organic-scout's proposed_checks discipline) PLUS an orchestrator content/safety gate before approval, side-effect-free and preferring project-declared tooling — refusal classes (network access, state mutation outside the target repo, privilege escalation, interpreter one-liners over remote/generated content) refused regardless of attestation; see orchestrator-protocol.md → Amendment ingestion
  cost_of_denial: "<one line — what the objective loses if denied>"
executive_summary: "1-2 sentences"
model_used: "..."
context_resolution: ...
```

**Protected-path denylist (authoritative — the single source both sides of the channel
reference).** `proposed_expected_files` may never name a path matching one of these classes; a
class match is disqualifying on its own, independent of how well-cited the entry's evidence is:

- VCS internals (`.git/` and everything under it, including hooks)
- CI/CD pipeline configs (`.github/`, `.gitlab-ci*`, `Jenkinsfile`, and equivalents)
- Agent-config roots (`.claude/`, `.opencode/`, `.agents/`, `.ai-team/`)
- Framework/tooling executable scripts — install and bootstrap scripts (`scripts/install.sh`,
  `adapters/*/install.sh` and equivalents) and shared-protocol script directories
  (`domain/skills/_shared/scripts/` and installed equivalents such as
  `{install_dir}/_shared/scripts/`) — these include the BLOCKING citation-audit gate
  (`orchestrator-protocol.md` → "Citation audit"); a worker writable there can neuter the review
  plane
- Every class `common-rules.md` → Principle 2 already names read-only for every delegated skill
  (shared protocols, SKILL.md files, project config files, CI/CD pipelines)

This denylist governs `proposed_expected_files` only — a worker-proposed widening of scope —
never the original brief's own `expected_files`, which the orchestrator declares directly,
outside this channel. `organic-implementer`'s matching Hard Rule and the orchestrator's Amendment
ingestion (both in their own files) cross-reference this list rather than repeating it.

**Rules:**
- The cap is 2 `paused` envelopes **per objective**, not per delegation — the orchestrator
  independently counts this objective's recorded `scope-amendment` entries and injects the
  running total as `amendment_requests_used` into every delegation and re-engage/replay prompt
  for the objective (`orchestrator-protocol.md` → Critical Context Forwarding); this skill's own
  counter starts from that injected value, never from zero on a re-engage. A third scope gap for
  the same objective, or a gap already denied — in this delegation or per the injected
  `amendments_denied` — is a terminal `blocked` with `scope_report` (`kind: scope-exceeds-brief`
  or `scope-large`) — never a third pause, and a denied gap never re-enters the pause condition.
- The orchestrator's answer arrives as a single continuation message in the same delegation, not
  a fresh delegation: `AMENDMENT APPROVED` (carrying the COMPLETE updated `expected_files` and
  `allowed_edit_roots` verbatim, plus any approved `proposed_checks` — the worker adopts these
  lists, never derives its own) or `AMENDMENT DENIED` (with the instruction to finish within the
  original scope or return a terminal `blocked`).
- An amendment request never asks a design question. A design question always remains
  `status: needs_input` (terminal) — `scope-amendment` is scoped to file/root gaps the evidence
  already proves, never to open decisions.
- A `paused` envelope does not consume the shared re-brief budget (DD-14,
  `orchestrator-protocol.md`) — see `orchestrator-protocol.md` → "Amendment ingestion" for the
  orchestrator-side handling, including folding `artifacts` into `group_files` immediately on
  receipt and the infra-death path for a worker that dies mid-pause.

## Review Receipt

Produced by `organic-reviewer` for every candidate Evidence-Tier Review classifies as tier ≥ 1 (schema: `orchestrator-protocol.md` → "Evidence-Tier Review"). Consumed by `work-unit-commits` (commit gate) and the orchestrator (routing, Re-engage Routing on `failure_class`). An absent receipt for a tier ≥ 1 candidate is a hard block on commit — `work-unit-commits` refuses without it.

```yaml
tier: 0 | 1 | 2
tier_reason: "<one line, mandatory — e.g. 'tier 2: modifies session auth middleware'>"
verdict: review-clear | review-blocked   # null only in a status:blocked context-failure envelope, where no review ran
lenses:
  correctness:
    status: pass | findings
    findings:
      - { id: "F-1", severity: CRITICAL | MAJOR | MINOR, confidence: high | medium | low, evidence: executed | read, trigger: "<one line — optional; REQUIRED when severity is MAJOR or CRITICAL and evidence is read>", file: "<path>", line: <int>, claim: "<one line>" }
  security:                # present only when the diff activated organic-security (tier 2)
    status: pass | findings
    findings:
      - { id: "F-2", severity: CRITICAL | MAJOR | MINOR, confidence: high | medium | low, evidence: executed | read, trigger: "<one line — optional; REQUIRED when severity is MAJOR or CRITICAL and evidence is read>", file: "<path>", line: <int>, claim: "<one line>" }
verification:
  - { command: "<verbatim>", exit_code: 0, outcome: pass | fail, gate: "<name>" }  # gate: optional, present only for review_gates outcomes
overrides:                 # user-accepted findings, if any — omit entirely when empty
  - { finding_id: "F-1", justification: "<user-supplied, one sentence>" }   # singular form — one finding
  - { finding_ids: ["F-3", "F-6"], justification: "<user-supplied, one sentence>" }   # bulk form — see Rules below
verdict_history:           # optional — present only on a delta-mode receipt; omit entirely on a full-pass receipt
  - { pass: full | delta, report: "<path to that pass's on-disk report>", verdict: review-clear | review-blocked, note: "<one line>" }
not_reverified:            # optional — present only on a delta-mode receipt; omit entirely on a full-pass receipt
  - "<one line — lens/file not re-checked this pass, and why: already clean in the prior pass | outside the delta scope>"
findings_addressed:        # optional — orchestrator-authored addendum for an inline closure (Evidence-Tier Review → Delta re-validation → "Inline closure"); omit entirely otherwise
  - { finding_id: "F-1", files: ["<repo-relative path>", "..."], fix_evidence: "<path:line or command output digest>", gate_results: "<pass|fail summary>" }
```

**Rules:**
- `tier_reason` is REQUIRED and non-empty for tier 1 and tier 2 — review cost is never unexplained.
- Every finding carries its own `confidence: high | medium | low` alongside `severity`. Coverage, not self-filtering, is the contract: a lens reports every finding it identifies — including ones it is uncertain about or considers low-severity — and never withholds one for importance or confidence; the orchestrator's downstream triage (accept-and-proceed, re-brief, delta re-validation) is the filter, not the lens itself. A `confidence: low` finding still counts fully toward the verdict below — low confidence narrows the recommended remediation path, never the verdict (fail closed).
- Every finding also carries `evidence: executed | read` — `executed` means the lens ran something (command, mutation probe, scenario, measurement against real data) whose observed result demonstrates the defect; `read` means the finding rests on code reading alone. `trigger` (optional in general) names the concrete input/command/state that reaches the cited line and produces the defect; it is REQUIRED whenever `severity` is MAJOR or CRITICAL and `evidence: read`. A `read` finding with no named `trigger` is emitted at `MINOR` as maximum — this caps the severity a lens may claim from reading alone, it never gates coverage: the finding is still reported, at every confidence level, exactly as the bullet above requires.
- **Precedence between the evidence cap and the confidence-fail-closed rule:** the evidence cap applies at emission, before the verdict is computed: a `read` finding without a named `trigger` is emitted at MINOR as maximum. The confidence rule then applies unchanged to the severity actually emitted — low confidence never downgrades an emitted severity, and a CRITICAL at any confidence still blocks. Consequently a CRITICAL or MAJOR with `evidence: read` always carries a `trigger`.
- `overrides` bulk form: an entry carries EITHER `finding_id: "F-1"` (singular) OR `finding_ids: ["F-3", "F-6", ...]` (list), never both, plus the existing `justification`. The bulk form is valid ONLY for findings that are `severity: MINOR` AND `evidence: read` without a `trigger`. Authorship is unchanged regardless of form — orchestrator-authored only, never the lens (see Principle 4, `common-rules.md`).
- `verdict` is REQUIRED for tier ≥ 1: `review-blocked` when ≥ 1 CRITICAL finding exists in `organic-reviewer`'s own lenses, at ANY confidence level; `review-clear` otherwise (MAJOR/MINOR findings alone do not block, regardless of confidence). `organic-reviewer` alone computes and emits this field (`organic-reviewer/SKILL.md` → Hard Rules); `work-unit-commits` gates its commit on it (see `work-unit-commits/SKILL.md` → Decision Gates).
- `lenses.security` is present only when Evidence-Tier Review activated `organic-security` (tier 2); omit it entirely for tier 1.
- Every `findings[]` entry's `claim` MUST resolve to a `file:line` citation — this is the receipt-side half of the Citation audit in `orchestrator-protocol.md` → "Evidence-Tier Review"; a claim without a resolvable citation is a contract violation.
- `overrides` is populated only when the user accepted-and-proceeded over a finding instead of re-engaging the worker; omit the field entirely when no override occurred.
- `verdict_history` is present only on a delta-mode receipt (`orchestrator-protocol.md` → Evidence-Tier Review → Delta re-validation): one entry per pass in the chain — the initial full pass, then every delta pass since, oldest first. **Chain custody:** the orchestrator is the chain's custodian — it injects the prior receipt's full `verdict_history` array as `delta_scope.prior_verdict_history` (Critical Context Forwarding) alongside `prior_report`; `organic-reviewer` appends EXACTLY ONE entry, its own pass, and returns the full resulting chain — it never reconstructs earlier entries from the report text. The LAST entry's `verdict` is authoritative for the commit gate (`work-unit-commits`, Decision Gates) and MUST mirror this receipt's own top-level `verdict` field; an earlier entry recording `review-blocked` does not itself block once a later entry clears it. A receipt whose last entry disagrees with the top-level `verdict` is a contract violation — `work-unit-commits` fails closed on it (`work-unit-commits/SKILL.md` → Decision Gates), never silently picking one field over the other. Omit the field entirely for a full-pass receipt.
- `not_reverified` is present only on a delta-mode receipt: the areas/lenses/files the prior pass covered that this pass did not re-check, mirroring the on-disk report's mandatory "Not Re-Verified" list (`organic-reviewer/references/report-format.md` → Delta Report Variant) — carrying the coverage gap into the envelope itself, since the orchestrator ingests only the envelope and never reads the report's full contents (Purpose above). Omit the field entirely for a full-pass receipt.
- `findings_addressed` is an optional, orchestrator-authored addendum — mirroring `overrides`, `organic-reviewer` never writes it — recording an inline closure per `orchestrator-protocol.md` → Evidence-Tier Review → Delta re-validation → "Inline closure". Eligible only when ALL of: the receipt's own top-level `verdict` was ALREADY `review-clear` before the closure (a `review-blocked` receipt is never cleared this way), every closed finding's fix was mechanically prescribed by the finding text itself (never CRITICAL), and the closure touched only files already in the receipt's `group_files`. One entry per finding closed this way, citing the fix evidence and the re-run gate results — an entry without gate evidence is invalid. Each entry's `files` field is REQUIRED: the repo-relative paths the closure actually touched — a digest-only `fix_evidence` never substitutes for it. An entry missing `files`, or naming any file outside `group_files`, is invalid and fails the commit gate closed (`work-unit-commits/SKILL.md` → Decision Gates) — a fail-closed gate never treats a pathless entry as an implicit pass. Never used for a CRITICAL finding, and never alters the receipt's top-level `verdict` field — an addendum records that a closure happened, it does not re-compute the gate.
- A `verification[]` entry carrying `gate:` is an objective `review_gates` outcome from `.ai-team/config.yaml` — exit code only, always `confidence: high` (objective exit-code evidence, not a judgment call). A failing gate additionally lands as a `lenses.correctness.findings[]` entry: `file`/`line` cite the gate's declaring entry in `.ai-team/config.yaml` (always a resolvable citation), and `claim` names gate name + command + exit code. A failing blocking gate is CRITICAL and forces `verdict: review-blocked`; a failing non-blocking gate is MAJOR and does not block.
- Tier 0 candidates produce no receipt — the result envelope alone is the record.

## Rules

1. **Always return an envelope** — even on failure
2. **Summary over detail** — provide enough context for the orchestrator to act without reading the full detail section
3. **Paths are relative** — always relative to the target project root
4. **No code in envelope** — include outcome, counts, and key risks — reserve code snippets for the detail sections
5. **Honest status** — report `status: warning` or `status: blocked` (return `status: ok` only when all checks pass)

## Examples

### Successful Scout Bootstrap

```yaml
status: ok
executive_summary: "Bootstrapped project config. Detected stack (<frameworks> + <language(s)> + <package manager>). Generated config.yaml."
artifacts:
  - name: "config"
    path: ".ai-team/config.yaml"
next_recommended: []
model_used: "sonnet"
context_resolution: "none"
```

### Blocked — Scope Exceeds Brief

```yaml
status: blocked
executive_summary: "Cannot implement the billing-export objective without touching services/billing/tax.py, which the Task Brief does not declare."
artifacts: []
scope_report:
  kind: scope-exceeds-brief
  detail: "Export totals require the tax module's rounding helper; not in expected_files."
  target: null
  needed_files: ["services/billing/tax.py"]
next_recommended: ["extend expected_files and allowed_edit_roots, then re-brief"]
risks:
  - "Objective may need a wider brief before implementation can proceed"
model_used: "sonnet"
context_resolution: "self-loaded"
```

### Paused — Scope Amendment Requested

```yaml
status: paused
artifacts:
  - { name: "endpoint (partial)", path: "services/billing/export.py" }
artifacts_omitted: 0
amendment_request:
  kind: scope-amendment
  reason: "Export totals require the tax module's rounding helper; not in expected_files."
  evidence: "services/billing/export.py:88 calls Tax::round(), defined at services/billing/tax.py:12"
  proposed_expected_files:
    - { action: MODIFY, path: "services/billing/tax.py", evidence: "services/billing/export.py:88 calls the undeclared Tax::round() helper" }
  proposed_checks: []
  cost_of_denial: "Export totals round incorrectly; the billing-export objective fails its own acceptance check."
executive_summary: "Billing-export implementation paused pending one file addition; awaiting the orchestrator's amendment decision."
model_used: "sonnet"
context_resolution: "self-loaded"
```

### Cache Miss After Compaction

```yaml
status: ok
executive_summary: "Implemented the billing-export endpoint per the Task Brief; both acceptance checks passed."
artifacts:
  - name: "endpoint"
    path: "services/billing/export.py"
next_recommended: []
risks:
  - "Orchestrator did not inject current_iso_utc — recovered via `date -u +%Y-%m-%dT%H:%M:%SZ`. Likely a compaction event."
model_used: "sonnet"
context_resolution: "fallback"
```
