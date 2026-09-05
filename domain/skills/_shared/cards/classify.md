# Card: classify

> Read when: a request arrives and `ai-team status` shows no task in progress.

Every request is classified **aloud**, before any file is touched:

| Class | Signal | What happens |
|---|---|---|
| question / probe | the user wants an answer or an experiment | answer or try it; nothing is saved |
| bounded change | you can settle it after reading 1–3 files yourself | four lines in chat, the user's yes, one task with one phase |
| large change | anything else: new flow, several surfaces, unknown territory | design first (card: design) |

In doubt, the heavier class. Mid-task a class only goes up, never down. If a "bounded"
change needs a 4th file to understand, it was large: say so and switch.

## Bounded change

1. Read the 1–3 files yourself. Ask the questions that matter, one message.
2. Write the four lines in chat, in the user's language:
   **objective** (the observable result) · **decisions** (invariants in plain words, each with
   how it is demonstrated) · **check** (a runnable command) · **out of scope**.
3. Wait for the yes. Then, verbatim:
   ```
   ai-team new <slug> --kind bounded
   ai-team plan generate --objective "…" --decision "…" [--decision "…"] --check "…" [--check "…"] --out-of-scope "…" --file <path> [--file <path>]
   ```
4. Card: delegate.

## Large change

```
ai-team new <slug> --kind large
```
Then card: design. A large change never skips the design because "it is clear".

## The user's word wins

"hazlo tú" / "do it yourself" → you implement inline, no sub-agents, no machine ceremony
beyond saying so. "delega" → the machine's route, even for a small thing. Never argue.

## Decision test

A constraint is an invariant, not a mechanism: if the sentence stays true when the
implementer rewrites the function from scratch, it is a decision; otherwise it is a
mechanism and does not belong in the four lines (a regex, a `startswith`, a file layout).
