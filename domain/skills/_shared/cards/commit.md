# Card: commit

> Read when: `ai-team status` allows `commit-check --phase n`.

```
ai-team commit-check --phase <n>
```
Exit 0 means: implementer settled `ok`/`warning`, tier declared, and — above tier 0 — every
lens report re-validates unchanged since its `settle` (drift refuses, naming the ticket and
the path), every CRITICAL it carries is ruled, and every MAJOR is ruled or deferred. Exit 1
lists what is missing; that list is the next action.

## The commit — the one thing you do to the tree

1. Stage exactly the phase's files, by path: `git status --porcelain` ∩ (expected files ∪
   artifacts). A dirty path outside the set belongs to someone else and stays unstaged.
2. One Conventional Commit per phase (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`),
   body in plain words, authored by the user alone (no trailer names an AI). `git push` waits
   for the user's word.
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
