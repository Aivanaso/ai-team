# Envelope Examples — sdd-security

Standard result envelope per `_shared/result-envelope.md`, with sdd-security-specific fields.

## Envelope Schema

```yaml
status: ok | warning | blocked | failed
executive_summary: "..."
mode: threat-model | code-audit
artifacts:
  - name: threat-model | audit-report
    path: .ai-team/changes/{name}/threat-model.md | audit-report.md
findings: []   # list of per-finding structures
security_requirements: []   # threat-model only; empty list for code-audit
verdict: no-findings | warnings-only | critical
suppressed_count: 0
next_recommended:
  - "spec"    # after threat-model
  - "verify"  # after code-audit
risks: []
model_used: opus | sonnet
context_resolution: injected | fallback | none
```

`verdict` drives the gate:
- `no-findings` → no override prompt needed
- `warnings-only` → no override prompt; findings surface in the report
- `critical` → orchestrator presents the 3-option override prompt to the user

## Variant 1: threat-model, no findings

```yaml
status: ok
executive_summary: "Threat model complete. No security findings. Temporal sweep: no temporal fields detected."
mode: threat-model
artifacts:
  - name: threat-model
    path: .ai-team/changes/my-change/threat-model.md
findings: []
security_requirements: []
verdict: no-findings
suppressed_count: 0
next_recommended:
  - "spec"
risks: []
model_used: opus
context_resolution: injected
```

## Variant 2: threat-model, warnings only

```yaml
status: ok
executive_summary: "Threat model complete. 2 warnings found (no CRITICAL). Spec phase should ingest the security_requirements."
mode: threat-model
artifacts:
  - name: threat-model
    path: .ai-team/changes/my-change/threat-model.md
findings:
  - id: F-1
    category: auth/authz
    file_line: proposal.md:34
    severity: WARNING
    description: "Session tokens have no explicit expiry policy stated."
    exploit_scenario: "An attacker who obtains a session token could use it indefinitely."
    recommendation: "Add a MUST requirement for session token TTL to the spec."
    confidence_rationale: "Proposal does not mention expiry anywhere (grep confirms)."
security_requirements:
  - req_text: "Session tokens MUST expire after at most 24 hours of inactivity."
    priority: MUST
    related_touchpoint: "auth/authz"
verdict: warnings-only
suppressed_count: 1
next_recommended:
  - "spec"
risks: []
model_used: opus
context_resolution: injected
```

## Variant 3: threat-model, CRITICAL finding

```yaml
status: warning
executive_summary: "Threat model complete. 1 CRITICAL finding: hardcoded API key in proposal approach section. Override required to proceed."
mode: threat-model
artifacts:
  - name: threat-model
    path: .ai-team/changes/my-change/threat-model.md
findings:
  - id: F-1
    category: env-secrets
    file_line: proposal.md:52
    severity: CRITICAL
    description: "Proposal approach shows hardcoded API key in code snippet."
    exploit_scenario: "Key committed to repository would be accessible to any repository reader."
    recommendation: "Remove hardcoded key. Use environment variable injection."
    confidence_rationale: "Proposal text contains a literal API key string (confirmed by grep)."
security_requirements:
  - req_text: "API keys MUST NOT appear in source code. MUST be injected via environment variables."
    priority: MUST
    related_touchpoint: "env-secrets"
verdict: critical
suppressed_count: 0
next_recommended:
  - "spec"
risks:
  - "CRITICAL finding F-1 requires user override to proceed"
model_used: opus
context_resolution: injected
```

## Variant 4: code-audit, all clean

```yaml
status: ok
executive_summary: "Code audit complete. All 5 categories clean. 12 files audited, 3 1-hop callers read."
mode: code-audit
artifacts:
  - name: audit-report
    path: .ai-team/changes/my-change/audit-report.md
findings: []
security_requirements: []
verdict: no-findings
suppressed_count: 0
next_recommended:
  - "verify"
risks: []
model_used: sonnet
context_resolution: injected
```

## Variant 5: blocked (invalid mode)

```yaml
status: blocked
executive_summary: "Invalid mode: 'scan'. Expected threat-model or code-audit."
mode: scan
artifacts: []
findings: []
security_requirements: []
verdict: no-findings
suppressed_count: 0
next_recommended: []
risks:
  - "Invalid mode value; cannot proceed"
model_used: sonnet
context_resolution: injected
```

## Variant 6: blocked (missing mode in context)

```yaml
status: blocked
executive_summary: "Required field 'mode' is missing from injected context. Cannot determine which workflow to run."
mode: null
artifacts: []
findings: []
security_requirements: []
verdict: no-findings
suppressed_count: 0
next_recommended: []
risks:
  - "mode: missing from injected context"
model_used: sonnet
context_resolution: fallback
```
