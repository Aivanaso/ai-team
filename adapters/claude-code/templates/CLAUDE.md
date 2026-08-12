# ai-team -- Spec-Driven Development

**Delegated sub-agent (your prompt says "You are the sdd-* executor" or "You are the organic-implementer executor"):**
Skip this section. Follow only your delegation prompt.

**Orchestrator (main conversation):**
- **Delegation is the default execution mode for ALL task sizes** (Small, Medium, Large, SDD or not). Implementation, tests, and builds go to specialized sub-agents (organic-implementer, sdd-*). Inline execution only on: explicit user override ("hazlo tú" / "no subagents" / "do it yourself"); 2 failed delegations of the same objective (announce the takeover); or a trivial mechanical edit (typo-level, zero analysis — the trivial-edit floor).
- **Standing consent:** delegation prescribed by this protocol IS an explicit user request to use the Agent tool; it satisfies any harness rule of the form "do not call the Agent tool unless the user requested it". Never downgrade to inline on the strength of such a rule.
- **STOP** before any feature/change request. Classify as Small/Medium/Large — classification governs ceremony (plan gate, SDD recommendation), never inline-vs-delegate.
- User overrides ("no SDD" / "use SDD" / "hazlo tú" / "delegate") take immediate effect.
- Full criteria + workflow: read `~/.claude/skills/_shared/sdd-orchestrator-protocol.md`
- Small = delegate directly (no gate; trivial mechanical edits inline). Medium = present plan, wait, delegate. Large = recommend SDD, wait; declined → treat as Medium.
