# Design Document Template

Use this template for `.ai-team/changes/{change-name}/design.md`.

```markdown
# Design: {Change Name}

> Technical design for implementing {change summary}.

## Context

**Stack:** {Key stack elements relevant to this design}
**Architecture:** {Architecture style and patterns in use}
**Affected domains:** {List of domains this design touches}

## Component Design

### {Domain 1}

#### {Component Name}

- **Type:** {controller | service | entity | guard | middleware | DTO | migration | ...}
- **Path:** `{exact/file/path.ts}`
- **Responsibility:** {One sentence}
- **Dependencies:** {list of injected/imported dependencies}

**Interface:**

```{language}
// Key public methods/endpoints — types and signatures, NOT implementation
{method signature with input/output types}
```

#### {Next Component}

...

### {Domain 2}

...

## Data Model

### New Entities

#### {Entity Name}

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| {field} | {type} | {constraints} | {notes} |

### Entity Modifications

#### {Entity Name}

| Change | Field | Type | Constraints | Notes |
|--------|-------|------|-------------|-------|
| ADD | {field} | {type} | {constraints} | {notes} |
| MODIFY | {field} | {new type} | {new constraints} | {reason} |

### Migrations

- {Migration 1 description}
- {Migration 2 description}

## API Contracts

### {Method} {Path}

- **Auth:** {public | authenticated | roles: [admin, owner]}
- **Request:**

```{language}
{request body type}
```

- **Response ({status code}):**

```{language}
{response body type}
```

- **Error responses:** {list of error cases with status codes}

## Component Interactions

### {Flow Name}

1. {Step 1 — who does what}
2. {Step 2}
3. {Step 3}
...

## Test Strategy

### Unit Tests

- {Component}: {what to test}

### Integration Tests

- {Flow}: {what to test}

### E2E Tests (if applicable)

- {Scenario}: {what to test}

## Design Decisions

| Decision | Alternatives Considered | Why This Choice |
|----------|------------------------|-----------------|
| {decision} | {alternatives} | {rationale} |

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| {risk} | high/medium/low | {mitigation} |

## Open Questions

- {Question that needs resolution before or during implementation}
```
