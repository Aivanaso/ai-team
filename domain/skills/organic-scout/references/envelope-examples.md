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

## Discover — success, scope_proposal requested

```yaml
status: ok
executive_summary: "Discovery pass for 'billing export' with scope_proposal requested. Chain closes to ExportService, InvoiceRepository, and the repository's existing test double."
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
  scope_proposal:
    expected_files:
      - { action: CREATE, path: "src/billing/services/ExportService.ts", evidence: "src/billing/services/InvoiceService.ts:40 — export-then-notify flow to replicate" }
      - { action: MODIFY, path: "src/billing/repositories/InvoiceRepository.ts", evidence: "src/billing/repositories/InvoiceRepository.ts:12 — new export query needs a method added here" }
      - { action: CREATE, path: "tests/billing/services/ExportService.test.ts", evidence: "tests/billing/services/InvoiceService.test.ts:1 — sibling test file for the existing analogue" }
      - { action: MODIFY, path: "tests/Double/billing/InvoiceRepositoryStub.ts", evidence: "tests/Double/billing/InvoiceRepositoryStub.ts:8 — object-literal stub builds InvoiceRepository and needs the new method added" }
    construction_sites_swept: true
    acceptance_checks:
      - { command: "npm test -- tests/billing/services/ExportService.test.ts", verified: "target exists at package.json:14 (\"test\": \"vitest run\")", expect: "exit 0" }
      - { command: "npm run typecheck", verified: "executed read-only, exit 0 on current tree", expect: "exit 0" }
    public_contracts:
      - "ExportService.export(invoiceIds: string[]): Promise<ExportResult> — new public method (does not exist yet, modeled on InvoiceService.ts:40)"
      - "InvoiceRepository.findForExport(ids: string[]): Promise<Invoice[]> — new interface member, src/billing/repositories/InvoiceRepository.ts:12"
    constraints_candidates:
      - "InvoiceService never returns partial results on a failed batch item — it fails the whole export instead (src/billing/services/InvoiceService.ts:55)"
      - "InvoiceRepository.findByIds silently drops ids beyond the 500-parameter query limit — callers chunk first (src/billing/repositories/InvoiceRepository.ts:20)"
    file_dossier:
      - { path: "src/billing/repositories/InvoiceRepository.ts", documented_gotchas: ["docblock at src/billing/repositories/InvoiceRepository.ts:20 — findByIds silently drops ids beyond the 500-parameter query limit; callers chunk first"], external_conditions: [], constructor_deps: { count: 2, cap: "4-5 (CLAUDE.md:41 'Max 4-5 constructor dependencies')" } }
      - { path: "tests/Double/billing/InvoiceRepositoryStub.ts", documented_gotchas: [], external_conditions: [] }
    open_scope_questions:
      - "Retention policy for generated exports has no existing caller — cannot cite evidence for a cleanup job path."
    plan_proposal:
      - { title: "Repository can find invoices for export", behavior: "InvoiceRepository exposes findForExport(ids) and its test double builds it", demonstrating_check: { command: "npm run typecheck", verified: "executed read-only, exit 0 on the current tree; goes red the moment InvoiceRepository gains findForExport until tests/Double/billing/InvoiceRepositoryStub.ts:8 implements it — this slice's red", expect: "exit 0" }, contract_left: "InvoiceRepository.findForExport(ids: string[]): Promise<Invoice[]> — src/billing/repositories/InvoiceRepository.ts:12", decisions_candidates: [], files: ["src/billing/repositories/InvoiceRepository.ts", "tests/Double/billing/InvoiceRepositoryStub.ts"] }
      - { title: "ExportService exports a batch of invoices", behavior: "ExportService.export(invoiceIds) returns an ExportResult using the repository query from slice 1", demonstrating_check: { command: "npm test -- tests/billing/services/ExportService.test.ts", verified: "fails today because src/billing/services/ExportService.ts does not exist yet — a CREATE slice's red (target exists at package.json:14)", expect: "exit 0" }, contract_left: "ExportService.export(invoiceIds: string[]): Promise<ExportResult> — created by this brief: src/billing/services/ExportService.ts", decisions_candidates: ["a failed batch item fails the whole export, never partial results (src/billing/services/InvoiceService.ts:55)"], files: ["src/billing/services/ExportService.ts", "tests/billing/services/ExportService.test.ts"] }
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
