# Envelope Examples — sdd-scout

Result envelopes for each mode. Return the appropriate variant.

## Bootstrap — success

```yaml
status: ok
executive_summary: "Detected TypeScript/NestJS monorepo (pnpm, DDD architecture). Generated config.yaml with 2 bounded contexts (orders, customers) and cqrs+repository-pattern."
artifacts:
  - name: "config"
    path: ".ai-team/config.yaml"
next_recommended: []
model_used: "sonnet"
context_resolution: "none"
```

## Bootstrap — ambiguous stack

```yaml
status: ok
executive_summary: "Generated config.yaml. Stack partially detected: TypeScript confirmed, no framework markers found (no next/nestjs/astro). Defaulted architecture to 'unknown'. Review and adjust config.yaml before running sdd-propose."
artifacts:
  - name: "config"
    path: ".ai-team/config.yaml"
risks:
  - "Architecture style defaulted to 'unknown' — no recognizable directory pattern found. Review bounded_contexts before running propose."
next_recommended: []
model_used: "sonnet"
context_resolution: "none"
```

## Explore — success

```yaml
status: ok
executive_summary: "Explored 'authentication flow'. Found 8 relevant files. JWT tokens issued by AuthService; refresh handled in middleware; frontend stores token in httpOnly cookie. Recommend extracting refresh logic into a dedicated RefreshTokenService."
artifacts:
  - name: "exploration"
    path: ".ai-team/explorations/authentication-flow/findings.md"
next_recommended: []
model_used: "sonnet"
context_resolution: "injected"
```

## Explore — topic not found

```yaml
status: ok
executive_summary: "Explored 'payment webhooks'. No files matching the topic found in source tree. Either the feature does not exist yet or is implemented under a different name (searched: webhook, stripe, payment)."
artifacts:
  - name: "exploration"
    path: ".ai-team/explorations/payment-webhooks/findings.md"
risks:
  - "Zero matches. findings.md documents what was searched and why results are empty."
next_recommended: []
model_used: "sonnet"
context_resolution: "injected"
```

## Baseline — success

```yaml
status: ok
executive_summary: "Generated baseline spec for 'shops'. Documented 7 requirements from 12 source files (entity, 4 services, controller, 3 DTOs, migration, 2 tests). 3 open questions flagged for review."
artifacts:
  - name: "spec"
    path: ".ai-team/specs/shops/spec.md"
risks:
  - "Baseline is inferred from code — user should review for accuracy"
next_recommended: []
model_used: "sonnet"
context_resolution: "injected"
```

## Baseline — low confidence

```yaml
status: ok
executive_summary: "Generated baseline spec for 'notifications'. 4 requirements extracted. Low confidence: domain boundary unclear (logic split across notifications/ and users/ services). 5 open questions flagged."
artifacts:
  - name: "spec"
    path: ".ai-team/specs/notifications/spec.md"
risks:
  - "Baseline is inferred from code — user should review for accuracy"
  - "Domain boundary unclear: some notification logic lives in users/services/UserService.ts (see open questions in spec)"
next_recommended: []
model_used: "sonnet"
context_resolution: "injected"
```
