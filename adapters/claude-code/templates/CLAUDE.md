# ai-team -- Spec-Driven Development

**Delegated sub-agent (your prompt says "You are the sdd-* executor"):**
Skip this section. Follow only your delegation prompt.

**Orchestrator (main conversation):**
- **STOP** before any feature/change request. Classify as Small/Medium/Large.
- User overrides ("no SDD" / "use SDD" / "hazlo tú" / "delegate") take immediate effect.
- Full criteria + workflow: read `~/.claude/skills/_shared/sdd-orchestrator-protocol.md`
- Small = act. Medium = present plan, wait. Large = recommend SDD, wait.
