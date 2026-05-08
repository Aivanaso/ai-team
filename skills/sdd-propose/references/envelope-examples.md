# Envelope Examples — sdd-propose

Result envelope variants. Copy the matching variant and fill the placeholders.

---

## ok — Successful Proposal

```yaml
status: ok
executive_summary: "Proposal for {change-name}. Affects {N} domains ({list}). {Key approach summary}. {N} risks identified, {N} open questions."
change_type: "infra" | "feature" | "mixed"
security_touchpoints: []   # empty list = not security-sensitive; non-empty = list of touchpoint slugs
artifacts:
  - name: "proposal"
    path: ".ai-team/changes/{change-name}/proposal.md"
  - name: "state"
    path: ".ai-team/changes/{change-name}/state.yaml"
next_recommended:
  - "spec"   # omit if change_type is "infra" — orchestrator may skip spec
  - "design"
model_used: "{resolved-model}"
context_resolution: "injected"
```

---

## needs_input — Request Too Vague

```yaml
status: needs_input
executive_summary: "Cannot produce proposal — user request is too vague to derive testable acceptance criteria."
artifacts: []
next_recommended: []
questions:
  - "{Specific question 1 to clarify scope}"
  - "{Specific question 2 to clarify expected behavior}"
model_used: "{resolved-model}"
context_resolution: "injected"
```

---

## warning — Conflicting Request

```yaml
status: warning
executive_summary: "Proposal for {change-name} produced. WARNING: {conflict description}. User must resolve before spec phase."
change_type: "feature" | "mixed"
security_touchpoints: []
artifacts:
  - name: "proposal"
    path: ".ai-team/changes/{change-name}/proposal.md"
  - name: "state"
    path: ".ai-team/changes/{change-name}/state.yaml"
next_recommended:
  - "spec"
  - "design"
risks:
  - "{Conflict description and which existing spec/code it contradicts}"
model_used: "{resolved-model}"
context_resolution: "injected"
```

---

## blocked — Change Already Has Proposal

```yaml
status: blocked
executive_summary: "Cannot create proposal — change directory already contains a proposal.md."
artifacts: []
next_recommended: ["continue"]
risks:
  - "Change {change-name} already has a proposal. Use /ai-team continue to resume."
model_used: "{resolved-model}"
context_resolution: "injected"
```

---

## failed — Unrecoverable Error

```yaml
status: failed
executive_summary: "Propose phase failed. {Error description}."
artifacts: []
next_recommended: []
risks:
  - "{Error detail}"
model_used: "{resolved-model}"
context_resolution: "injected" | "fallback"
```
