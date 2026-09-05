# Envelope Examples — organic-scout

## Bootstrap — success

```yaml
status: ok
executive_summary: "Bootstrapped project config. Detected <language> + <framework> + <test runner>, package manager <name>. Wrote config.yaml with commit_strategy: auto."
mode: bootstrap
artifacts:
  - { name: "config", path: ".ai-team/config.yaml" }
next_recommended: []
risks:
  - "Architecture style defaulted to 'unknown' — no recognizable directory pattern found. Review bounded_contexts before the first design."
model_used: "sonnet"
context_resolution: "none"
```

## Bootstrap — blocked (config exists)

```yaml
status: blocked
executive_summary: "config.yaml already exists at .ai-team/config.yaml; bootstrap never overwrites it."
mode: bootstrap
artifacts: []
next_recommended: []
risks: []
model_used: "sonnet"
context_resolution: "none"
```

## Map — success

```yaml
status: ok
executive_summary: "Mapped 'billing export': the flow lives in ExportController → ExportService → InvoiceRepository; the closest analogue is the CSV report export; two documented gotchas and one external condition found."
mode: map
artifacts:
  - { name: "map report", path: ".ai-team/explorations/2026-09-05-billing-export-map.md" }
discovery_report:
  key_files:
    - { path: "src/Billing/ExportController.php", role: "entry point", evidence: "src/Billing/ExportController.php:24" }
    - { path: "src/Billing/ExportService.php", role: "assembles rows", evidence: "src/Billing/ExportService.php:41" }
    - { path: "src/Report/CsvReportExporter.php", role: "analogue to follow", evidence: "src/Report/CsvReportExporter.php:18" }
  patterns:
    - "exporters stream rows through a generator (src/Report/CsvReportExporter.php:30)"
  documented_gotchas:
    - "InvoiceRepository::forPeriod() loads eagerly; docblock warns above 10k rows (src/Billing/InvoiceRepository.php:57)"
  external_conditions:
    - "the legacy cron only exports invoices with status = paid (crontab.d/billing:3 → bin/legacy-export.sh:12)"
  risks: []
  open_questions:
    - "No retention policy for generated exports exists — a decision for the design's ## Fuera de alcance or ## Decisiones"
next_recommended: []
risks: []
model_used: "sonnet"
context_resolution: "self-loaded"
```

## Scope — success

```yaml
status: ok
executive_summary: "Scoped the approved design's 2 phases: 4 files with evidence, 3 checks verified runnable and able to fail, 2 anchored constraint candidates; the report ends with the scope-report json block."
mode: scope
artifacts:
  - { name: "scope report", path: ".ai-team/explorations/2026-09-05-billing-export-scope.md" }
discovery_report:
  key_files:
    - { path: "src/Billing/ExportService.php", role: "phase 1 MODIFY", evidence: "src/Billing/ExportService.php:41" }
    - { path: "src/Billing/Export/RowBuilder.php", role: "phase 1 CREATE — insertion site", evidence: "src/Billing/ExportService.php:44 will call it" }
  patterns: []
  risks: []
  open_questions:
    - "phase 2's check `composer phpcs` covers src/Billing/ (phpcs.xml:14) — verified; no runner covers bin/ scripts"
scope_phases: 2
next_recommended: []
risks: []
model_used: "sonnet"
context_resolution: "self-loaded"
```

The report's final block, for the same pass (fenced as ```json in the report itself):

```text
{"kind": "scope-report", "phases": [
  {"n": 1, "expected_files": [
     {"action": "MODIFY", "path": "src/Billing/ExportService.php", "evidence": "src/Billing/ExportService.php:41"},
     {"action": "CREATE", "path": "src/Billing/Export/RowBuilder.php", "evidence": "src/Billing/ExportService.php:44 (insertion site)"}],
   "acceptance_checks": [{"command": "vendor/bin/phpunit tests/Billing/ExportServiceTest.php", "verified": "executed read-only: 4 tests; deleting the new assertion makes it fail", "expect": "exit 0"}],
   "constraints_candidates": ["exports include only status = paid invoices — bin/legacy-export.sh:12"],
   "open_questions": []},
  {"n": 2, "expected_files": [{"action": "MODIFY", "path": "src/Billing/ExportController.php", "evidence": "src/Billing/ExportController.php:24"}],
   "acceptance_checks": [{"command": "composer phpcs", "verified": "phpcs.xml:14 covers src/Billing/", "expect": "exit 0"}],
   "constraints_candidates": [], "open_questions": []}
]}
```

## Scope — blocked (design not approved)

```yaml
status: blocked
executive_summary: "The injected design .ai-team/designs/2026-09-05-billing-export.md has status: draft; scope runs against an approved design only."
mode: scope
artifacts: []
next_recommended: ["approve the design (`ai-team design approve`) then relaunch the scope pass"]
risks: []
model_used: "sonnet"
context_resolution: "self-loaded"
```

## Map — needs_input (topic matches zero files)

```yaml
status: needs_input
executive_summary: "Topic 'loyalty points' matches no file, directory or symbol in the project."
mode: map
artifacts: []
questions:
  - "Is this greenfield (no analogue to map) or a naming mismatch? Name a file or symbol if the latter."
next_recommended: []
risks: []
model_used: "sonnet"
context_resolution: "self-loaded"
```
