# Spec Convention

> Format and rules for writing specs in the ai-team system.

## Purpose

Specs are the **source of truth** for what the system does. They live in `.ai-team/specs/{domain}/spec.md` and are committed to git. Every feature, behavior, and constraint MUST be traceable to a spec.

## Spec Structure

```markdown
# {Domain Name}

> One-line description of this domain.

## Overview

Brief description of the domain's purpose, scope, and boundaries.

## Requirements

### REQ-{DOMAIN}-{NNN}: {Requirement Title}

{Description of the requirement.}

**Priority:** MUST | SHOULD | MAY

#### Scenarios

**Given** {precondition}
**When** {action}
**Then** {expected outcome}

**Given** {another precondition}
**When** {action}
**Then** {expected outcome}

### REQ-{DOMAIN}-{NNN}: {Next Requirement}

...

## Decisions

| ID | Decision | Rationale | Date |
|----|----------|-----------|------|
| DEC-{DOMAIN}-001 | {What was decided} | {Why} | YYYY-MM-DD |

## Dependencies

- {Other domain or external system this depends on}
```

## RFC 2119 Keywords

Use these keywords with their standard meanings (per [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119)):

| Keyword | Meaning |
|---------|---------|
| **MUST** / **SHALL** | Absolute requirement |
| **MUST NOT** / **SHALL NOT** | Absolute prohibition |
| **SHOULD** | Recommended, but exceptions exist with justification |
| **SHOULD NOT** | Discouraged, but exceptions exist with justification |
| **MAY** | Truly optional |

## Base Specs vs Delta Specs

There are two types of specs in the system:

| Type | Location | Purpose | Created by |
|------|----------|---------|------------|
| **Base spec** | `.ai-team/specs/{domain}/spec.md` | Complete truth of what exists | sdd-scout (baseline mode) or merged deltas |
| **Delta spec** | `.ai-team/changes/{name}/specs/{domain}/spec.md` | What's changing | sdd-spec agent |

### Base Specs

A base spec documents **everything a domain currently does**. For new projects, the first base spec is created by the sdd-spec agent. For **existing projects**, the sdd-scout generates a baseline by reading the current code.

Base specs are the foundation. Delta specs describe changes relative to them. Without a base spec, a delta has no context — the system will auto-generate a baseline before allowing delta creation.

### Lifecycle

```
Existing code → [baseline] → base spec → [change] → delta spec → [archive] → updated base spec
                                                                                    ↑
New domain   → [first change] → base spec (from first full spec) ──────────────────┘
```

## Domain Organization

Specs are organized by business domain, NOT by technical layer:

```
.ai-team/specs/
├── auth/spec.md          # Authentication & authorization
├── billing/spec.md       # Payments, subscriptions, invoices
├── notifications/spec.md # Email, push, in-app notifications
└── user/spec.md          # User profiles, preferences
```

**Good domains:** `auth`, `billing`, `search`, `notifications`
**Bad domains:** `controllers`, `services`, `database`, `frontend`

## Delta Specs

During active changes, agents write **delta specs** — partial specs that describe ONLY what changed:

```markdown
# {Domain Name} — Delta

## ADDED

### REQ-AUTH-004: OAuth2 Provider Support

The system MUST support Google and GitHub as OAuth2 providers.

**Given** a user clicks "Sign in with Google"
**When** the OAuth2 flow completes successfully
**Then** the user is authenticated and a session is created

## MODIFIED

### REQ-AUTH-001: Login Flow

~~The system MUST authenticate users via email and password.~~

The system MUST authenticate users via email/password OR OAuth2 provider.

## REMOVED

### REQ-AUTH-002: Legacy Token Auth

> Removed: replaced by OAuth2 in REQ-AUTH-004.
```

### Delta Sections

| Section | Meaning |
|---------|---------|
| `ADDED` | New requirements not in the current spec |
| `MODIFIED` | Changes to existing requirements (show before → after) |
| `REMOVED` | Requirements being deleted (include reason) |

## Merge Algorithm

When archiving a completed change, delta specs merge into base specs:

1. **ADDED** sections → append to the domain's spec
2. **MODIFIED** sections → replace the matching requirement in-place
3. **REMOVED** sections → delete the matching requirement, add entry to Decisions table
4. Update the `Decisions` table with any new decisions
5. Increment requirement numbers if needed to avoid gaps

## Rules

1. **One spec per domain** — never split a domain across files
2. **Requirements are immutable during a phase** — modify only through delta specs
3. **Every requirement has scenarios** — no requirement without at least one Given/When/Then
4. **IDs are stable** — once assigned, a requirement ID never changes (removed IDs are retired)
5. **Specs are committed** — base specs in `.ai-team/specs/` are ALWAYS committed to git
6. **Deltas are temporary** — delta specs in `.ai-team/changes/` are gitignored and merged on archive
