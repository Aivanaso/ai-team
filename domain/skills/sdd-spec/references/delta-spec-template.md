# Delta Spec Template

Use this template when an affected domain already has a base spec (existing code + existing `spec.md`).

```markdown
# {Domain Name} — Delta

> Change: {change-name}
> Proposal ACs covered: {list of AC numbers this delta addresses}

## ADDED

### REQ-{DOMAIN}-{NNN}: {Requirement Title}

{Description of the requirement.}

**Priority:** MUST | SHOULD | MAY
**Source:** AC-{N} from proposal
**Cross-ref:** {REQ-OTHER-NNN if applicable}

#### Scenarios

**Given** {precondition}
**When** {action}
**Then** {expected outcome}

## MODIFIED

### REQ-{DOMAIN}-{NNN}: {Existing Requirement Title}

~~{Original text from base spec}~~

{New text with the modification.}

**Reason:** {Why this requirement changed}
**Source:** AC-{N} from proposal

#### Scenarios

{Updated scenarios reflecting the modification}

## REMOVED

### REQ-{DOMAIN}-{NNN}: {Requirement Being Removed}

> Removed: {reason, with reference to the replacing requirement if applicable}
```

## Notes

- Only include the sections (ADDED / MODIFIED / REMOVED) that apply — omit empty sections.
- The highest existing `REQ-{DOMAIN}-NNN` in the base spec determines the starting number for new IDs. Continue the sequence; never reuse removed IDs.
- Every scenario must be behavioral — describe what the user/system observes, not internal implementation details.

**Good scenario:**
```
Given a user with email "ivan@example.com" already exists
When a new registration request arrives with the same email
Then the system rejects with a 409 Conflict error
And the existing account is not modified
```

**Bad scenario (too technical):**
```
Given the UserRepository contains an entity with email "ivan@example.com"
When UserService.register() is called
Then it throws DuplicateEmailException
```
