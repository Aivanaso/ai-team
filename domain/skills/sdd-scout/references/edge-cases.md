# Edge Cases — sdd-scout

Handling for non-happy-path scenarios per mode.

## Bootstrap Edge Cases

### config.yaml already exists

**Condition:** `.ai-team/config.yaml` exists when bootstrap mode runs.

**Action:** Do NOT overwrite. Return `status: blocked` with message:
> "config.yaml already exists at `.ai-team/config.yaml`. Delete it manually if you want to regenerate, or use explore mode to investigate the current stack."

**Rationale:** Overwriting a user-edited config silently would destroy conventions and architecture decisions the team made.

---

### Monorepo with multiple stacks

**Condition:** Project root has `pnpm-workspace.yaml` and child packages use different languages/frameworks (e.g., `backend/` is NestJS, `frontend/` is Astro).

**Action:**
1. Set `project.type: monorepo`.
2. Detect stack per package separately.
3. In `stack.languages`, list all distinct languages.
4. In `stack.frameworks`, list all detected frameworks (one entry per framework with its package path as a note).
5. In `conventions`, note "monorepo: each package has its own tsconfig/eslint".
6. In `architecture.bounded_contexts`, list each workspace package as a top-level context.

**Example output fragment:**
```yaml
project:
  type: monorepo
stack:
  frameworks:
    - name: nestjs
      version: "10.x"
      note: "packages/backend/"
    - name: astro
      version: "4.x"
      note: "packages/frontend/"
```

---

### Ambiguous architecture (two signals conflict)

**Condition:** Directory scan finds both `src/*/domain/` paths (DDD signal) AND flat `src/controllers/` (layered signal).

**Action:**
1. Default to `ddd` if `domain/application/infrastructure/` pattern appears inside at least 2 feature folders.
2. Default to `layered` if only top-level technical directories exist.
3. If genuinely ambiguous: set `style: unknown`, add an `open_question` entry in the config (as a YAML comment), and include a risk in the envelope.

---

### No clear language detected

**Condition:** None of the standard manifest files (`package.json`, `composer.json`, `go.mod`, `Cargo.toml`, `pyproject.toml`, `Gemfile`) exist in the project root.

**Action:**
1. Scan for source file extensions: `.ts`, `.js`, `.php`, `.go`, `.rs`, `.py`, `.rb`.
2. Use the dominant extension as the language hint.
3. Set `stack.languages[0].version: "unknown"`.
4. Add risk to envelope: "No package manifest found — language version not confirmed."

---

### Single-file project or very small repo

**Condition:** Project root has fewer than 5 source files total.

**Action:** Generate a minimal config.yaml (project, stack, no architecture detection). Add envelope risk: "Very small project — architecture detection skipped."

---

## Explore Edge Cases

### Topic too broad

**Condition:** `topic` matches >50 files (e.g., "types" or "utils").

**Action:**
1. Narrow the search with more specific patterns (function names, class names, route paths).
2. If still >50 matches after narrowing, read only the top 15 most relevant files (ranked by match density).
3. Note in findings.md: "Search returned {N} files; analysis limited to top 15 by relevance."

---

### Topic matches zero files

**Condition:** Grep/glob returns 0 results for the topic.

**Action:** Write a findings.md that documents:
- Exact search terms tried
- Directory scope searched
- Conclusion: "Feature appears absent from codebase or named differently"

Return `status: ok` (not `fail`) — "nothing found" is a valid finding.

---

## Baseline Edge Cases

### Domain does not map to a clear directory

**Condition:** The requested domain (e.g., "invoicing") has no dedicated directory — its logic is scattered across multiple modules.

**Action:**
1. Search by entity names, route paths, and service method names rather than directories.
2. List all files found under "Key Files" in the spec.
3. Add an open question: "Invoicing logic is not bounded in a single directory — recommend extracting to `src/invoicing/` in a future refactor."

---

### No tests exist for the domain

**Condition:** Baseline scan finds no test files for the domain.

**Action:** Document requirements from source code only. Mark all REQs with lower confidence indicator `[inferred — no tests]`. Add open question: "No tests found for this domain — confidence in behavior accuracy is lower."

---

### Domain logic split across multiple frameworks (monorepo)

**Condition:** `shops` domain has logic in both `packages/backend/src/shops/` (NestJS) and `packages/frontend/src/pages/shops/` (Astro/React).

**Action:**
1. Document backend requirements (API, services, entities) first.
2. Add a single frontend REQ per [frontend granularity rule](../SKILL.md) that groups all UI pages.
3. Note in the spec overview which package each section was extracted from.
