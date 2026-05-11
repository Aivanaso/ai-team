# Scaffold Templates

> Dispatch table and empty scaffold templates for test scaffold generation (REQ-TASKS-020).
> Loaded by sdd-tasks at Step 7b when `config.yaml.stack.testing` is non-empty.

## Dispatch Table

| Framework token | File pattern | Block style |
|-----------------|--------------|-------------|
| `vitest` | `{name}.spec.ts` | `describe` + `it` |
| `jest` | `{name}.spec.ts` / `{name}.test.ts` | `describe` + `it` |
| `pytest` | `test_{name}.py` | `class Test{Name}` + `def test_` |
| `phpunit` | `{Name}Test.php` | `class {Name}Test extends TestCase` + `public function test_` |
| unrecognised | `{name}.spec.txt` | prose description |

## Template: vitest / jest

```typescript
import { describe, it, expect } from 'vitest'; // or 'jest'

// Scaffold for AC-{N}: {AC description}
// REQ-IDs: {REQ-DOMAIN-NNN}, ...

describe('{Feature under test}', () => {
  // Given: {precondition}
  // When: {action}
  // Then: {expected outcome}
  it('{scenario name from spec}', () => {
    // TODO: implement per REQ-{DOMAIN}-{NNN}
    expect(true).toBe(false); // red — fails until implemented
  });
});
```

## Template: pytest

```python
import pytest

# Scaffold for AC-{N}: {AC description}
# REQ-IDs: {REQ-DOMAIN-NNN}, ...

class Test{FeatureName}:
    # Given: {precondition}
    # When: {action}
    # Then: {expected outcome}
    def test_{scenario_name}(self):
        # TODO: implement per REQ-{DOMAIN}-{NNN}
        assert False, "red — fails until implemented"
```

## Template: phpunit

```php
<?php

use PHPUnit\Framework\TestCase;

// Scaffold for AC-{N}: {AC description}
// REQ-IDs: {REQ-DOMAIN-NNN}, ...

class {FeatureName}Test extends TestCase
{
    // Given: {precondition}
    // When: {action}
    // Then: {expected outcome}
    public function test_{scenario_name}(): void
    {
        // TODO: implement per REQ-{DOMAIN}-{NNN}
        $this->fail('red — fails until implemented');
    }
}
```

## Template: unrecognised (placeholder)

```
# Scaffold for AC-{N}: {AC description}
# File: {name}.spec.txt (no runner detected — prose placeholder)
# REQ-IDs: {REQ-DOMAIN-NNN}, ...

Scenario: {scenario name from spec}
  Given: {precondition}
  When: {action}
  Then: {expected outcome}

  Status: NOT IMPLEMENTED — replace this file with a real test once a test runner is configured.
```

## Manual Review Checklist Template (meta-project path)

> Used when `config.yaml.stack.testing: []`. Insert into tasks.md as `## Manual Review Checklist`.

| Criterion ID | REQ-ID covered | Bash command | Expected result | Maps to |
|---|---|---|---|---|
| C-{N} | REQ-{DOMAIN}-{NNN} | `{grep or ls command}` | {exit code or match count} | COMPLIANT if {condition}; FAILING otherwise |
