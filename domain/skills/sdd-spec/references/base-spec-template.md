# Base Spec Template

Use this template when an affected domain is **greenfield** (no existing code, no existing `spec.md`).
The resulting file becomes the base spec when the change is archived.

```markdown
# {Domain Name}

> {One-line description of the domain's purpose}

## Overview

{Domain purpose, scope, boundaries — derived from proposal and stack context.}

## Requirements

### REQ-{DOMAIN}-001: {Requirement Title}

{Description of the requirement.}

**Priority:** MUST | SHOULD | MAY
**Source:** AC-{N} from proposal
**Cross-ref:** {REQ-OTHER-NNN if applicable, else omit}

#### Scenarios

**Given** {precondition}
**When** {action}
**Then** {expected outcome}

### REQ-{DOMAIN}-002: {Requirement Title}

{Description.}

**Priority:** MUST | SHOULD | MAY
**Source:** AC-{N} from proposal

#### Scenarios

**Given** {precondition}
**When** {action}
**Then** {expected outcome}

## Decisions

| ID | Decision | Rationale | Date |
|----|----------|-----------|------|
| DEC-{DOMAIN}-001 | {Decision made during spec} | {Why} | {YYYY-MM-DD} |

## Dependencies

- {Other domains this domain depends on — or "None" if standalone}
```

## Notes

- Start IDs at `001`; never skip numbers.
- Mark this artifact as `type: full` in the result envelope (not `delta`).
- The Decisions table captures design choices made during spec authoring, not implementation choices — those go in `state.yaml.decisions:`.
- Dependencies list other domains by name, not by file path.
