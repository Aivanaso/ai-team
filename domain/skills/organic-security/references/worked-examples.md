# Worked Examples — organic-security

## 1. Temporal Invariant Sweep: auth-magic-link Retrospective

This worked example shows how the Temporal Invariant Sweep applies retroactively to a
magic-link auth change. Use it as a reference when running the sweep in threat-model mode.

| Field | Read path | Enforcement in scope | Sweep result |
|-------|-----------|-----------------------|--------------|
| `magic_link_tokens.expires_at` | `POST /v1/auth/verify` | Yes | OK |
| `magic_link_tokens.consumed_at` | `POST /v1/auth/verify` | Yes | OK |
| `sessions.revoked_at` | AuthGuard per-request | Yes (MUST) | OK |
| **`sessions.refresh_expires_at`** | **`POST /v1/auth/refresh`** | **Not stated** | **MINOR — emit finding** |

The fourth row (`sessions.refresh_expires_at`) is the finding that slipped past an earlier
design pass and was only caught by a later code-audit. With the sweep, this finding fires
before code is written — and converts into a `MUST` security requirement a follow-up Task
Brief must implement.

**Finding that would have been emitted:**

`evidence`/`trigger` are N/A in threat-model mode — these findings route through
`security_requirements`, never into the Review Receipt or the commit gate.

```
id: F-1
category: temporal-invariant-sweep
file_line: (scope_description reference — sessions schema definition)
severity: MINOR
confidence: medium
description: "sessions.refresh_expires_at is defined in the schema but the change scope
  does not state that POST /v1/auth/refresh rejects requests where refresh_expires_at
  < now. No enforcement clause referenced."
exploit_scenario: "An attacker who obtains a refresh token that has expired at the
  policy layer could continue refreshing sessions indefinitely, bypassing the token
  rotation TTL."
recommendation: "Add a MUST requirement: POST /v1/auth/refresh MUST reject tokens
  where refresh_expires_at < now with HTTP 401."
confidence_rationale: "Scope description defines the column and lists the endpoint in
  scope; grep over the schema finds no 'refresh_expires_at' check clause."
```

---

## 2. Audit Prompt: Five Vulnerability Categories (Full Detail)

Apply these five categories to every candidate diff (code-audit) or scope description
(threat-model). Each category below includes the complete heuristics for what to look for.

### Category 1: Input Validation

Look for: SQL injection, command injection, XXE, template injection, path traversal.

Check that user-supplied input is validated, sanitised, and never passed directly to:
- Database queries (raw SQL strings built from user data, e.g., `"SELECT * FROM users WHERE id=" + userId`)
- Shell commands (`exec`, `child_process.spawn`, `system()`, `popen()` with user-controlled arguments)
- XML parsers with external entity resolution enabled (XXE)
- Template engines (server-side template injection, e.g., Jinja2, Twig, Handlebars with user templates)
- File paths (path traversal: `../../../etc/passwd` via unvalidated path components)

Heuristics for code-audit: grep for `.execute(`, `.query(`, `exec(`, `execSync(`, `spawn(`, `readFile(`, `join(path,` in `group_files` and 1-hop callers. Trace arguments back to HTTP request objects.

Heuristics for threat-model: look for scope-description language mentioning "user input is passed to", "search query from user", "file path from request", "dynamic query".

### Category 2: Authentication & Authorization

Look for: authentication bypass, privilege escalation, broken session management, JWT vulnerabilities.

Verify that every endpoint or function that operates on sensitive resources:
- Enforces authentication (requires a valid session or token before any processing)
- Checks the caller's permission level against the resource being accessed (e.g., user can only read their own records, admin endpoints require admin role)
- Does not rely solely on client-supplied data to determine identity (e.g., `userId` from a non-signed request body)

JWT-specific: check for `alg: none` acceptance, weak secrets, missing expiry validation, missing issuer/audience validation.

Session-specific: check for missing invalidation on logout, session fixation, missing CSRF protection on state-changing endpoints.

### Category 3: Cryptography & Secrets

Look for: hardcoded credentials, weak algorithms, key storage issues, weak randomness, missing certificate validation.

Hardcoded credentials: API keys, passwords, tokens appearing as string literals in source files. Grep for `apiKey =`, `password =`, `secret =`, `token =` with adjacent string literals.

Weak algorithms:
- MD5 or SHA1 used for password hashing (should be bcrypt/argon2/scrypt)
- DES, 3DES, RC4 for symmetric encryption (should be AES-256-GCM)
- RSA keys < 2048 bits

Weak randomness: `Math.random()`, `rand()`, `random.random()` used for security-sensitive values (tokens, nonces, salts). These are not cryptographically secure.

Missing certificate validation: `rejectUnauthorized: false`, `verify=False`, `InsecureSkipVerify: true` in HTTP client configuration.

Key storage: private keys or secrets committed to repository, stored in plain config files (not environment variables or a secrets manager).

### Category 4: Injection & Code Execution

Look for: RCE via unsafe deserialization, `eval`/`exec` on user input, XSS, prototype pollution.

Unsafe deserialization: `pickle.loads()`, `unserialize()`, `ObjectInputStream` without allowlist, `yaml.load()` (unsafe loader in Python PyYAML), `JSON.parse()` with subsequent `eval()`. Any deserialization of data from an untrusted network source using a format that can encode executable code.

eval/exec on user input: `eval(userInput)`, `new Function(userInput)`, `exec(userInput)`, `execfile(userInput)`. Even indirect: user input used as a key to select a function that is then called.

XSS: user-supplied content rendered into HTML without escaping. In React/JSX: `dangerouslySetInnerHTML`. In templates: `{{ variable | safe }}`, `{!! $variable !!}` (Laravel), `{% autoescape off %}` around user content.

Prototype pollution (JavaScript/TypeScript): `Object.assign({}, userInput)` where userInput is not schema-validated; `_.merge({}, userInput)` before lodash patching; recursive merge functions that do not skip `__proto__` and `constructor`.

### Category 5: Data Exposure

Look for: sensitive data in logs, PII leakage in API responses, debug info exposed to end users, over-permissive responses.

Sensitive data in logs: passwords, tokens, credit card numbers, SSNs, or full request bodies logged. Check logger calls in authentication paths.

PII leakage: API responses that return full user objects (including email, phone, address) when only one field was requested. Check serializers, DTOs, and response mappers — are they field-scoped?

Debug information: stack traces, internal file paths, database error messages returned to the HTTP client. Check error handlers — do they catch and sanitize before responding?

Over-permissive responses: endpoints that return a list of all users when only the calling user's data was requested; admin-level fields (internal IDs, audit timestamps) returned to non-admin callers.

Error message information leakage: HTTP 500 responses that include the exception message verbatim, which may contain SQL query structure, file system paths, or library version strings.
