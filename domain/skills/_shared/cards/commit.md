# Card: commit

> Read when: `ai-team status` allows `commit-check --phase n`.

```
ai-team commit-check --phase <n>
```
Exit 0 means: implementer settled `ok`/`warning`, tier declared, and — above tier 0 — the
lens reports re-validated just now, clear or blocked only by ruled CRITICALs. Exit 1 lists
what is missing; do that, not a workaround.

## The commit — the one thing you do to the tree

1. Stage exactly the phase's files: `git status --porcelain` ∩ (expected files ∪ artifacts).
   Never `git add -A`; a dirty path outside the set belongs to someone else.
2. One Conventional Commit per phase (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`),
   body in plain words. Never a `Co-Authored-By` or any AI attribution. Never `git push`
   unless the user asked.
3. `commit_strategy: manual` in `.ai-team/config.yaml` → show the staged set and wait.
4. Record it:
   ```
   ai-team phase done <n> --commit <hash>
   ```
   A commit that closes a parked finding also flips its row:
   `ai-team debt fix --match "<origin or file:line>" --commit <hash>`.

## Checkpoint

Tell the user in their language: what the phase delivered, what it cost (the balance line of
`ai-team status`), what is next. The next phase waits for their word unless they said to run
through ("hazlo todo seguido", "tira hasta el final"). Last phase committed → card: close.
