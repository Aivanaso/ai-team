# Envelope Examples — organic-scout

Result envelopes for each mode. Return the appropriate variant.

## Bootstrap — success

```yaml
status: ok
executive_summary: "Detected TypeScript/NestJS monorepo (pnpm, DDD architecture). Generated config.yaml with 2 bounded contexts (orders, customers) and cqrs+repository-pattern."
artifacts:
  - { name: "config", path: ".ai-team/config.yaml" }
next_recommended: []
model_used: "sonnet"
context_resolution: "none"
```

## Bootstrap — ambiguous stack

```yaml
status: ok
executive_summary: "Generated config.yaml. Stack partially detected: TypeScript confirmed, no framework markers found. Defaulted architecture to 'unknown'. Review and adjust config.yaml before delegating."
artifacts:
  - { name: "config", path: ".ai-team/config.yaml" }
risks:
  - "Architecture style defaulted to 'unknown' — no recognizable directory pattern found. Review bounded_contexts before the next Task Brief."
next_recommended: []
model_used: "sonnet"
context_resolution: "none"
```

## Discover — success (pre-brief pass)

```yaml
status: ok
executive_summary: "Discovery pass for 'billing export'. Found 8 relevant files. Existing ExportService pattern to follow; two open questions on retention policy."
artifacts: []
discovery_report:
  key_files:
    - { path: "src/billing/services/InvoiceService.ts", role: "closest existing analogue — same export-then-notify flow", evidence: "src/billing/services/InvoiceService.ts:40" }
    - { path: "src/billing/repositories/InvoiceRepository.ts", role: "repository pattern to follow for the new export query", evidence: "src/billing/repositories/InvoiceRepository.ts:12" }
  patterns:
    - "Repository pattern: interface in domain/, implementation in infrastructure/ (src/billing/repositories/InvoiceRepository.ts:1)"
  risks:
    - "No existing retention policy for generated exports — needs a decision before the Task Brief sets out_of_scope"
  open_questions:
    - "Should the export include soft-deleted invoices? No existing caller answers this (searched InvoiceService, InvoiceRepository)."
next_recommended: []
model_used: "sonnet"
context_resolution: "self-loaded"
```

## Discover — topic not found

```yaml
status: ok
executive_summary: "Discovery pass for 'payment webhooks'. No files matching the topic found in the source tree. Either the feature does not exist yet or is implemented under a different name."
artifacts: []
discovery_report:
  key_files: []
  patterns: []
  risks:
    - "Zero matches (searched: webhook, stripe, payment). Feature likely does not exist yet."
  open_questions:
    - "Confirm with the user whether this is greenfield or a naming mismatch before writing the Task Brief."
next_recommended: []
model_used: "sonnet"
context_resolution: "self-loaded"
```
