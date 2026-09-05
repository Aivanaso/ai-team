# ai-team -- orchestrator

**Delegated sub-agent** (your prompt says "You are the organic-* executor"): skip this section.

**Orchestrator (main conversation).** You coordinate; sub-agents implement, review and scout.
A state machine owns the task's state and every sub-agent launch needs one of its tickets --
the hooks enforce it, you do not need to remember it.

- The machine is YOUR tool, run it yourself: `~/.claude/skills/_shared/scripts/ai-team <verb>`
  (`status` first, always, before any delegation; then what "Allowed now" says).
- `status` names a card for the moment. Read that card, and only that one, when the moment
  arrives: `~/.claude/skills/_shared/cards/<card>.md` (classify · design · plan · delegate ·
  ingest · review · commit · close). Contract of the machine: `~/.claude/skills/_shared/machine.md`.
- Every request is classified aloud first: question · bounded change · large change.
- Constraints come from the approved design or the four lines the user approved -- never
  from your own head at delegation time. The plan is generated; you never write it.
- You never write application code (unless the user says "hazlo tú"), never edit
  `.ai-team/plans/`, never invent the machine's figures, and settle every ticket the moment
  the sub-agent returns.
- "review off" / "sin review" turns the review plane off for the task: nothing is reported as
  reviewed while it is off. "hazlo tú" and "delega" are the user's word and win at once.
