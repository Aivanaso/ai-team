# Envelope Examples — sdd-spec

## Status: ok (all domains specced)

```yaml
status: ok
executive_summary: "Generated delta specs for {change-name}. {N} domains: {list}. {total} requirements ({added} added, {modified} modified, {removed} removed). Full traceability to {M} proposal ACs."
artifacts:
  - name: "spec-{domain}"
    path: ".ai-team/changes/{change-name}/specs/{domain}/spec.md"
    type: delta
  - name: "state"
    path: ".ai-team/changes/{change-name}/state.yaml"
next_recommended:
  - "design"
model_used: "{resolved-model}"
context_resolution: "injected"
```

## Status: ok (greenfield domain — full spec)

```yaml
status: ok
executive_summary: "Generated full spec for greenfield domain {domain} and delta spec for {domain2}. {total} requirements. Full traceability to {M} proposal ACs."
artifacts:
  - name: "spec-{domain}"
    path: ".ai-team/changes/{change-name}/specs/{domain}/spec.md"
    type: full
  - name: "spec-{domain2}"
    path: ".ai-team/changes/{change-name}/specs/{domain2}/spec.md"
    type: delta
  - name: "state"
    path: ".ai-team/changes/{change-name}/state.yaml"
next_recommended:
  - "design"
model_used: "{resolved-model}"
context_resolution: "injected"
```

## Status: warning (partial — some domains need baseline)

```yaml
status: warning
executive_summary: "Generated specs for {N} of {M} domains. Domains {list} need baseline specs before delta generation."
artifacts:
  - name: "spec-{domain}"
    path: ".ai-team/changes/{change-name}/specs/{domain}/spec.md"
    type: delta
  - name: "state"
    path: ".ai-team/changes/{change-name}/state.yaml"
next_recommended:
  - "baseline {domain1}"
  - "baseline {domain2}"
risks:
  - "Domains without baselines: {list}. Run baseline generation before continuing."
model_used: "{resolved-model}"
context_resolution: "injected"
```

## Status: blocked (no domains ready)

```yaml
status: blocked
executive_summary: "Cannot generate specs — all affected domains ({list}) need baseline specs first."
artifacts: []
next_recommended:
  - "baseline {domain1}"
  - "baseline {domain2}"
risks:
  - "No base specs exist for any affected domain. Baseline generation required."
model_used: "{resolved-model}"
context_resolution: "injected"
```

## Status: blocked (vague ACs — input needed)

```yaml
status: needs_input
executive_summary: "Proposal ACs {list} are too vague to decompose into requirements. Clarification needed before spec can proceed."
artifacts: []
next_recommended: []
risks:
  - "AC-{N}: '{text}' — ambiguous; cannot determine behavioral expectation."
model_used: "{resolved-model}"
context_resolution: "injected"
```
