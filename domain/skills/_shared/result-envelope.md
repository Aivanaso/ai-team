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
- An unverified hypothesis — the sub-agent verified the underlying defect/gap, not this fix —
  the orchestrator verifies it before acting on it (`orchestrator-protocol.md` → Recommendation
  ingestion), never treating it as a command
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
structured deviation block, `decisions_taken` (CAP 5, terminal envelopes only) for
behavioral decisions the brief did not fix, and `tdd_cycles` (CAP 5, terminal envelopes only)
for the red → green cycles the STRICT TDD MODE directive required. See that skill's Output
Contract for its complete field set.

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
# decisions_taken and tdd_cycles (with tdd_cycles_omitted / tdd_not_applicable) do NOT travel here — both are terminal-only (organic-implementer's Output Contract); a pause carries the fields declared in this block and nothing more.
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
- Any repo-local self-test suite for the shared-protocol gate scripts above (e.g. a
  `scripts/tests/` directory, and any installed equivalent) — a worker writable there could
  neuter the regression signal a future reviewer relies on for those protected scripts, even
  though such a suite never gates a live run

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

Produced by `organic-reviewer` for every candidate Evidence-Tier Review classifies as tier ≥ 1 (schema: `orchestrator-protocol.md` → "Evidence-Tier Review"). Consumed by the orchestrator (commit gate, routing, Re-engage Routing on `failure_class`). An absent receipt for a tier ≥ 1 candidate is a hard block on commit — the orchestrator refuses without it (`orchestrator-protocol.md` → "Commit creation").

**On-disk JSON sidecar.** The schema below is the receipt object as returned in the delegation
envelope; the orchestrator re-reads it from its on-disk sidecar for the fail-closed gate
immediately before the commit — the gate is this re-read, never the orchestrator's memory of an
earlier pass (`orchestrator-protocol.md` → **Commit creation**, step 1). For the on-disk copy, the lens
ALSO serializes this exact object — same field names, no additions, no renames — to a `.json`
sidecar next to its `.md` narrative report: `report_destination` with the `.md` extension
replaced by `.json` (e.g. `.ai-team/reviews/billing-export.md` →
`.ai-team/reviews/billing-export.json`), written in the same write step as the `.md` file
(`organic-reviewer/SKILL.md` Step 7, `organic-security/SKILL.md` code-audit Step 6). This
sidecar — never the `.md` file — is what the BLOCKING Citation audit
(`orchestrator-protocol.md` → Evidence-Tier Review) validates, via
`python3 skills/_shared/scripts/check-receipt.py receipt <sidecar> <project_root>`: a
Python-stdlib, JSON-only structural check (valid shape, CONTAINED on-disk resolution of every
cited `file` — `os.path.realpath` containment under `project_root` plus `os.path.isfile`, never
a bare existence check — the evidence→trigger coupling, verdict/`verdict_history` coherence,
`id` uniqueness after NFC normalization, the severity enum, lens `status`/findings coherence,
`kind` restricted to `"security-fragment"` or absent, a non-empty `verification[]` with
`{command, exit_code, outcome}` per row — or an empty one justified by `verification_omitted_reason` —
`not_reverified[]` as non-empty strings, and a `project_root` that is an existing directory other
than the filesystem root; an unusable citation string such as an embedded NUL is a VIOLATION, not
a crash) — it never re-runs a command and never opens the `.md` report.
`organic-security` in `threat-model` mode writes no sidecar (it never produces a `verdict` or
`lenses.correctness` object) — its report notes "no receipt sidecar in this mode" instead.

**`kind` — the FULL-receipt vs SECURITY-FRAGMENT discriminator.** A sidecar is a full reviewer
receipt by default. It is instead a security-lens fragment ONLY when it declares the top-level
`kind: "security-fragment"` field explicitly — `organic-security` (code-audit mode) always sets
it on the fragment it writes (`organic-security/SKILL.md` code-audit Step 6). The ABSENCE of
`lenses.correctness` is never itself the discriminator: a sidecar with no `kind` and no
`lenses.correctness` is a truncated full receipt (a contract violation), not a fragment. A
fragment MUST declare `lenses.security` and MUST NOT declare `lenses.correctness`; it never
carries a `verdict` field (only `organic-reviewer` computes that field), but if one is present
anyway it must be coherent with the fragment's own CRITICAL findings — `review-blocked` iff a
CRITICAL exists.

```yaml
kind: security-fragment  # OPTIONAL — omit entirely for a full reviewer receipt (the default);
                          # present ONLY on an organic-security code-audit fragment
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
verification_omitted_reason: "<one line>"   # ONLY when verification is [] on a full receipt (no candidate changes / every check unrunnable); MUST be absent otherwise — see Rules
overrides:                 # user-accepted findings, if any — omit entirely when empty
  - { finding_id: "F-1", justification: "<user-supplied, one sentence>" }   # singular form — one finding
  - { finding_ids: ["F-3", "F-6"], justification: "<user-supplied, one sentence>" }   # bulk form — see Rules below
verdict_history:           # optional — present only on a delta-mode receipt; omit entirely on a full-pass receipt
  - { pass: full | delta, report: "<path to that pass's on-disk report>", verdict: review-clear | review-blocked, note: "<one line>" }
not_reverified:            # optional — present only on a delta-mode receipt; omit entirely on a full-pass receipt
  - "<one line — lens/file not re-checked this pass, and why: already clean in the prior pass | outside the delta scope>"
findings_addressed:        # optional — orchestrator-authored addendum for an inline closure (Evidence-Tier Review → Delta re-validation → "Inline closure"); omit entirely otherwise
  - { finding_id: "F-1", files: ["<repo-relative path>", "..."], fix_evidence: "<path:line or command output digest>", gate_results: "<pass|fail summary>" }
exposure:                  # optional — orchestrator-authored addendum measuring real-data exposure for a queued CRITICAL/MAJOR finding whose trigger names a stored-data precondition (orchestrator-protocol.md → Exposure measurement for a stored-data precondition); omit entirely otherwise
  - { finding_id: "F-1", checked: true, precondition_rows: 42, total_rows: 1200, note: "<one line — what the measurement can and cannot rule out>" }   # checked: true — precondition_rows and total_rows REQUIRED
  - { finding_id: "F-2", checked: false, note: "<one line — why unmeasured>" }   # checked: false — precondition_rows and total_rows ABSENT; only finding_id, checked, note
```

**Rules:**
- `kind` (optional, top-level): absent or explicit `null` = a full reviewer receipt; the string `"security-fragment"` = the security lens's stand-alone sidecar (no `lenses.correctness`, no required `verdict`); ANY other value is a validator VIOLATION — a typo'd `kind` is never silently treated as a full receipt.
- `verification_omitted_reason` (optional, top-level): a full receipt whose `verification[]` is empty MUST carry this non-empty string naming the contract case that left nothing to re-run ("no candidate changes to review" — `group_files` empty; or "every declared check unrunnable in this environment"); it MUST be absent when `verification[]` is non-empty. A full receipt that re-ran nothing and says nothing is the zero-work class and fails the gate.
- `kind: "security-fragment"` is the ONLY discriminator between a full reviewer receipt and a
  security-lens fragment — see "kind" above. A full receipt (the default, `kind` absent) REQUIRES
  `lenses.correctness` and a top-level `verdict` in `VERDICTS`; a fragment REQUIRES
  `lenses.security` and forbids `lenses.correctness`. `check-receipt.py` fails closed on a sidecar
  that declares neither `kind` nor `lenses.correctness` — that shape is a truncated full receipt,
  never treated as an implicit fragment.
- `tier_reason` is REQUIRED and non-empty for tier 1 and tier 2 — review cost is never unexplained.
- Every finding carries its own `confidence: high | medium | low` alongside `severity`. Coverage, not self-filtering, is the contract: a lens reports every finding it identifies — including ones it is uncertain about or considers low-severity — and never withholds one for importance or confidence; the orchestrator's downstream triage (accept-and-proceed, re-brief, delta re-validation) is the filter, not the lens itself. A `confidence: low` finding still counts fully toward the verdict below — low confidence narrows the recommended remediation path, never the verdict (fail closed).
- Every finding also carries `evidence: executed | read` — `executed` means the lens ran something (command, mutation probe, scenario, measurement against real data) whose observed result demonstrates the defect; `read` means the finding rests on code reading alone. `trigger` (optional in general) names the concrete input/command/state that reaches the cited line and produces the defect; it is REQUIRED whenever `severity` is MAJOR or CRITICAL and `evidence: read`. A `read` finding with no named `trigger` is emitted at `MINOR` as maximum — this caps the severity a lens may claim from reading alone, it never gates coverage: the finding is still reported, at every confidence level, exactly as the bullet above requires.
- **Precedence between the evidence cap and the confidence-fail-closed rule:** the evidence cap applies at emission, before the verdict is computed: a `read` finding without a named `trigger` is emitted at MINOR as maximum. The confidence rule then applies unchanged to the severity actually emitted — low confidence never downgrades an emitted severity, and a CRITICAL at any confidence still blocks. Consequently a CRITICAL or MAJOR with `evidence: read` always carries a `trigger`.
- `overrides` bulk form: an entry carries EITHER `finding_id: "F-1"` (singular) OR `finding_ids: ["F-3", "F-6", ...]` (list), never both, plus the existing `justification`. The bulk form is valid ONLY for findings that are `severity: MINOR` AND `evidence: read` without a `trigger`. Authorship is unchanged regardless of form — orchestrator-authored only, never the lens (see Principle 4, `common-rules.md`). **Consequence for clearing a `review-blocked` verdict**: since the bulk form is structurally restricted to MINOR/read/no-trigger findings, it can never cover a CRITICAL finding — clearing a `review-blocked` receipt therefore REQUIRES a singular `finding_id` entry naming EVERY blocking CRITICAL finding, across BOTH `lenses.correctness` and `lenses.security` when tier 2 combines them (`orchestrator-protocol.md` → "Commit creation" enforces this at the commit gate; this is the same invariant stated once here rather than two independently-worded copies).
- `verdict` is REQUIRED for tier ≥ 1: `review-blocked` when ≥ 1 CRITICAL finding exists in `organic-reviewer`'s own lenses, at ANY confidence level; `review-clear` otherwise (MAJOR/MINOR findings alone do not block, regardless of confidence). `organic-reviewer` alone computes and emits this field (`organic-reviewer/SKILL.md` → Hard Rules); the orchestrator gates its commit on it (see `orchestrator-protocol.md` → "Commit creation").
- `lenses.security` is present only when Evidence-Tier Review activated `organic-security` (tier 2); omit it entirely for tier 1.
- Every `findings[]` entry's `claim` MUST resolve to a `file:line` citation — this is the receipt-side half of the Citation audit in `orchestrator-protocol.md` → "Evidence-Tier Review"; a claim without a resolvable citation is a contract violation.
- `overrides` is populated only when the user accepted-and-proceeded over a finding instead of re-engaging the worker; omit the field entirely when no override occurred.
- `verdict_history` is present only on a delta-mode receipt (`orchestrator-protocol.md` → Evidence-Tier Review → Delta re-validation): one entry per pass in the chain — the initial full pass, then every delta pass since, oldest first. **Chain custody:** the orchestrator is the chain's custodian — it injects the prior receipt's full `verdict_history` array as `delta_scope.prior_verdict_history` (Critical Context Forwarding) alongside `prior_report`; `organic-reviewer` appends EXACTLY ONE entry, its own pass, and returns the full resulting chain — it never reconstructs earlier entries from the report text. The LAST entry's `verdict` is authoritative for the commit gate (the orchestrator, `orchestrator-protocol.md` → "Commit creation") and MUST mirror this receipt's own top-level `verdict` field; an earlier entry recording `review-blocked` does not itself block once a later entry clears it. A receipt whose last entry disagrees with the top-level `verdict` is a contract violation — the orchestrator fails closed on it (`orchestrator-protocol.md` → "Commit creation"), never silently picking one field over the other. Omit the field entirely for a full-pass receipt.
- `not_reverified` is present only on a delta-mode receipt: the areas/lenses/files the prior pass covered that this pass did not re-check, mirroring the on-disk report's mandatory "Not Re-Verified" list (`organic-reviewer/references/report-format.md` → Delta Report Variant) — carrying the coverage gap into the envelope itself, since the orchestrator ingests only the envelope and never reads the report's full contents (Purpose above). Omit the field entirely for a full-pass receipt.
- `findings_addressed` is an optional, orchestrator-authored addendum — mirroring `overrides`, `organic-reviewer` never writes it — recording an inline closure per `orchestrator-protocol.md` → Evidence-Tier Review → Delta re-validation → "Inline closure". Eligible only when ALL of: the candidate's authoritative `verdict` was ALREADY `review-clear` before the closure — the correctness receipt's top-level `verdict`, which at tier 2 is the combined verdict the orchestrator derives from both lenses; a `kind: security-fragment` sidecar carries no `verdict` of its own and inherits this condition from that receipt (a `review-blocked` receipt is never cleared this way), every closed finding's fix was mechanically prescribed by the finding text itself (never CRITICAL), and the closure touched only files already in the receipt's `group_files`. Each entry's `finding_id` must resolve inside that same receipt document — the union of ITS OWN `lenses.correctness.findings[].id` and `lenses.security.findings[].id` — never across sidecars: at tier 2, a security-lens finding is closed on its own `kind: security-fragment` sidecar (the file carrying `lenses.security`), never on the correctness receipt, and a correctness-lens finding is closed on the correctness receipt instead. One entry per finding closed this way, citing the fix evidence and the re-run gate results — an entry without gate evidence is invalid. Each entry's `files` field is REQUIRED: the repo-relative paths the closure actually touched — a digest-only `fix_evidence` never substitutes for it. An entry missing `files`, or naming any file outside `group_files`, is invalid and fails the commit gate closed (`orchestrator-protocol.md` → "Commit creation") — a fail-closed gate never treats a pathless entry as an implicit pass. Never used for a CRITICAL finding, and never alters the receipt's top-level `verdict` field — an addendum records that a closure happened, it does not re-compute the gate.
- `exposure` is an optional, orchestrator-authored addendum — mirroring `findings_addressed`'s authorship pattern, `organic-reviewer` never writes it — recording a real-data exposure measurement for a CRITICAL or MAJOR finding whose `trigger` names a stored-data precondition, per `orchestrator-protocol.md` → Exposure measurement for a stored-data precondition. Each entry's `finding_id` must resolve inside this same receipt document — the union of `lenses.correctness.findings[].id` and `lenses.security.findings[].id` — exactly as `findings_addressed` resolves its own. Entry shape: `finding_id`, `checked` (bool — whether the measurement was actually taken), and `note` (one line recording what the measurement can and cannot rule out, e.g. a sampled scan vs. a full table count) are ALWAYS present. `precondition_rows` (int — rows matching the finding's stored-data precondition) and `total_rows` (int — the denominator the count was measured against) are present ONLY when `checked: true`; a `checked: false` entry carries `finding_id`, `checked`, and `note` alone — no `precondition_rows`, no `total_rows`. It never alters the receipt's top-level `verdict`, any finding's `severity`, or any `lenses.*` content — the addendum records a measurement, it does not re-compute the gate.
- The `exposure` addendum is taken AFTER the finding is emitted and BEFORE it is presented to the user, per `orchestrator-protocol.md` → Exposure measurement for a stored-data precondition, so its figures are already available when the finding is presented per `orchestrator-protocol.md` → Reporting to the user; the same figures also land in the matching `.ai-team/tech-debt.md` entry's exposure field when the finding is deferred there. A `checked: false` entry is valid — it records that the exposure question was considered and left unmeasured, never a silent omission — and `exposure` is never REQUIRED: a queued finding whose `trigger` names no stored-data precondition carries no entry at all.
- A `verification[]` entry carrying `gate:` is an objective `review_gates` outcome from `.ai-team/config.yaml` — exit code only, always `confidence: high` (objective exit-code evidence, not a judgment call). A failing gate additionally lands as a `lenses.correctness.findings[]` entry: `file`/`line` cite the gate's declaring entry in `.ai-team/config.yaml` (always a resolvable citation), and `claim` names gate name + command + exit code. A failing blocking gate is CRITICAL and forces `verdict: review-blocked`; a failing non-blocking gate is MAJOR and does not block.
- Tier 0 candidates produce no receipt — the result envelope alone is the record.

## Brief File Ledger JSON sidecar

The orchestrator maintains this sidecar next to a Brief File — `.ai-team/briefs/YYYY-MM-DD-
<slug>.json`, same slug as the `.md` Brief File — mirroring the `## Cost Ledger` table and
`## Close` section byte-for-byte in field meaning (`orchestrator-protocol.md` → Task Brief →
"Brief File (durable copy)"), kept in sync at every ledger append, at every `## Plan` approval
or `## Phases` checkbox change, and at the `## Close` write. No delegated skill writes this
file; it is orchestrator-authored only, exactly like the Brief File itself.

```json
{
  "ledger": [
    { "n": 1, "agent": "organic-implementer", "model": "opus", "tokens": 50000, "tool_uses": 12, "duration_s": 300, "outcome": "ok" }
  ],
  "close": {
    "delegations": 1,
    "subagent_tokens": 50000,
    "commits": ["<commit hash>", "..."],
    "re_briefs": 0,
    "inline_closures": [
      { "receipt": "<repo-relative path to a receipt .json sidecar>", "finding_ids": ["F-1", "..."] }
    ]
  },
  "plan": [
    { "n": 1, "title": "<one line>", "done": true }
  ]
}
```

`plan` is OPTIONAL and a top-level sibling of `ledger`/`close`, not nested under either — the
machine-checkable mirror of the `.md` Brief File's `## Plan` (the entry list) and `## Phases`
(the `done` flags): `done` mirrors that entry's `## Phases` checkbox. Absent or explicit `null`
means "not recorded" — a Small task's single-entry plan, or any Brief File written before this
field existed, validates as before EXCEPT the unconditional `close.commits` >= 1 floor, which
applies plan or no plan (D-D).

`close` is written only once `status` flips to `done` (mirrors the `.md` file's `## Close`
section — absent while the task is `active`/`paused`) — and the gate below has exactly one
prescribed invocation, immediately before that flip, so `close` is REQUIRED at the moment the
gate runs: `ledger` mode never accepts a missing `close` as "task still in progress, nothing to
check yet". Validated by `python3 skills/_shared/scripts/check-receipt.py ledger <sidecar>
[project_root]` (`orchestrator-protocol.md` → Task Brief → "Brief File structural check"). Every
check the validator performs, synced to the code (this doc follows the code, never the reverse —
a future change to `validate_ledger` updates this list in the same commit):

- `ledger` must be a list; every row must be an object.
- Each row's `n`, `tokens`, `tool_uses`, `duration_s` must be a plain integer — `true`/`false`
  and floats are rejected, not silently coerced. `tokens`, `tool_uses`, `duration_s` must also be
  ≥ 0. `n` must be unique across every row (no two rows share an identifier).
- Each row's `agent`, `model`, `outcome` must be a non-empty string.
- `close` is REQUIRED and must be an object.
- `close.delegations` must be a non-negative plain integer equal to `ledger`'s row count.
- `close.subagent_tokens` must be a non-negative plain integer equal to the sum of `ledger`'s
  `tokens` column.
- `close.commits` must be a list; every entry must be a non-empty string; and, whenever `close`
  is present as an object, the list must have at least 1 entry — a `close` with zero recorded
  commits is its own violation, regardless of whether `plan` (below) is present, `null`, or an
  empty list (`orchestrator-protocol.md` → "Commit creation": one atomic commit created inline by
  the orchestrator, once per objective, so a `close` is never valid with zero commits recorded).
  When `plan` IS a populated list, the length rule below (`close.commits` ≥ `plan`'s entry count)
  is a STRICTER floor stacked on top of this one, never a replacement for it.
- `close.re_briefs` must be a non-negative plain integer.
- A ledger row's `agent` is agnostic data the validator never inspects by name — a legacy row
  carrying a retired commit-creation worker's name remains VALID; commit evidence lives in
  `close.commits` and the Brief File's Phases checkboxes, never in a named ledger row
  (`orchestrator-protocol.md` → "Commit creation"; commit creation is not a delegation and gains
  no ledger row, `## Cost Ledger` in the same file).
- `close.inline_closures` is OPTIONAL — absent OR explicit `null` means no inline closures
  happened; every ledger sidecar written before this field existed validates exactly as it always
  did. When present (and non-null), it must be a list of `{ receipt, finding_ids }` objects:
  `receipt` is a non-empty, repo-relative path ENFORCED to end in `.json` that must exist and be
  CONTAINED under the validator's `project_root` argument (`ledger` mode accepts an optional
  `[project_root]` positional, defaulting to `.`, resolved with the same degenerate-root rule as
  receipt mode — a degenerate root short-circuits this entire check, before any cited receipt is
  opened); `finding_ids` is a non-empty list of non-empty strings, each compared — after Unicode
  NFC normalization, mirroring the duplicate-id check's own rationale — against that receipt's own
  `findings_addressed[].finding_id` values, themselves NFC-normalized the same way (the
  orchestrator's Inline closure procedure — `orchestrator-protocol.md` → Evidence-Tier Review →
  Delta re-validation — appends one such entry per inline closure it records). A `finding_ids`
  entry that is not a non-empty string (including a non-hashable JSON array/object) is its own
  VIOLATION and is simply excluded from the coverage comparison — never a crash, never escalated
  to exit 2.
- `plan` is OPTIONAL — absent OR explicit `null` means not recorded; every ledger sidecar
  written before this field existed validates as before EXCEPT the unconditional
  `close.commits` >= 1 floor, which applies plan or no plan (this doc follows the
  code, never the reverse — a future change to `_check_plan` updates this list in the same
  commit). When present it must be a list; every entry must be an object. Each entry's `n` must
  be a strict integer forming the sequence 1..N in order (entry `i` has `n == i + 1` — a gap, a
  repeat, a wrong start, or an out-of-order value is ONE violation naming the entry); `title`
  must be a non-empty string; `done` must be a strict boolean (`isinstance(v, bool)` —
  `"yes"`/`1`/`0` are violations, never coerced).
- When `close` is present as an object (the gate's one prescribed invocation, immediately
  before the `status:done` flip): every `plan` entry's `done` must be `true` (each `false` entry
  is its own violation naming the entry); and, when `close.commits` is a list, its length must
  be ≥ `plan`'s entry count — the orchestrator creates at least one commit per done plan entry
  (`orchestrator-protocol.md` → "Commit creation"). Before `close` (absent or not an object)
  neither of these two run. Every `plan` check is a pure shape/arithmetic check over
  already-parsed JSON — NO FILESYSTEM ACCESS, run unconditionally regardless of the
  degenerate-root rule above.

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
