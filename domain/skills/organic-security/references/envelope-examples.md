# Envelope Examples — organic-security

Standard result envelope per `_shared/result-envelope.md`, with organic-security's
`security_lens` block shaped for direct merge into the Review Receipt's `lenses.security`.

## Variant 1: threat-model, no findings

```yaml
status: ok
executive_summary: "Threat model complete. No security findings. Temporal sweep: no temporal fields detected."
mode: threat-model
artifacts: []
security_lens:
  status: pass
  findings: []
security_requirements: []
next_recommended: []
risks: []
model_used: "sonnet"
context_resolution: self-loaded
```

## Variant 2: threat-model, MINOR findings only

```yaml
status: ok
executive_summary: "Threat model complete. 2 MINOR findings (no CRITICAL), one at low confidence. Recommend folding security_requirements into the next Task Brief."
mode: threat-model
artifacts: []
security_lens:
  status: findings
  findings:
    - { id: "F-1", severity: MINOR, confidence: high, file: "src/auth/session.ts", line: 34, claim: "Session tokens have no explicit expiry policy stated in scope." }
    - { id: "F-2", severity: MINOR, confidence: low, file: "src/auth/session.ts", line: 41, claim: "Refresh token rotation may not invalidate the prior token; could not confirm from scope alone." }
security_requirements:
  - req_text: "Session tokens MUST expire after at most 24 hours of inactivity."
    priority: MUST
    related_touchpoint: "auth/authz"
next_recommended: []
risks: []
model_used: "sonnet"
context_resolution: self-loaded
```

## Variant 3: threat-model, CRITICAL finding

```yaml
status: warning
executive_summary: "Threat model complete. 1 CRITICAL finding (confidence: high): hardcoded API key in the described approach. Override required to proceed."
mode: threat-model
artifacts: []
security_lens:
  status: findings
  findings:
    - { id: "F-1", severity: CRITICAL, confidence: high, file: "src/config/keys.ts", line: 12, claim: "Hardcoded API key literal in source." }
security_requirements:
  - req_text: "API keys MUST NOT appear in source code. MUST be injected via environment variables."
    priority: MUST
    related_touchpoint: "env-secrets"
next_recommended: []
risks:
  - "CRITICAL finding F-1 requires user override to proceed"
model_used: "sonnet"
context_resolution: self-loaded
```

## Variant 4: code-audit (tier-2 lens), all clean

```yaml
status: ok
executive_summary: "Code audit complete for cache-invalidation. All 6 categories clean. 3 files audited, 2 1-hop callers read."
mode: code-audit
artifacts: []
security_lens:
  status: pass
  findings: []
security_requirements: []
next_recommended: []
risks: []
model_used: "sonnet"
context_resolution: self-loaded
```

## Variant 5: blocked (invalid mode)

```yaml
status: blocked
executive_summary: "Invalid mode: 'scan'. Expected threat-model or code-audit."
mode: scan
artifacts: []
security_lens:
  status: pass
  findings: []
security_requirements: []
next_recommended: []
risks:
  - "Invalid mode value; cannot proceed"
model_used: "sonnet"
context_resolution: self-loaded
```

## Variant 6: blocked (missing mode in context)

```yaml
status: blocked
executive_summary: "Required field 'mode' is missing from injected context. Cannot determine which workflow to run."
mode: null
artifacts: []
security_lens:
  status: pass
  findings: []
security_requirements: []
next_recommended: []
risks:
  - "mode: missing from injected context"
model_used: "sonnet"
context_resolution: fallback
```
