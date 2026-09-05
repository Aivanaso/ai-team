"""Claude Code hook entry points. JSON payload on stdin; the machine protects the
orchestrator from forgetting, not from sabotage: every internal error fails OPEN with one
line on stderr, never a traceback and never a block the orchestrator cannot explain.

pre-tool-use  PreToolUse on `Agent`: acts only when tool_input.subagent_type starts with
              `organic-`; walks up from the payload's cwd to `.ai-team/`; requires an open
              ticket of a compatible kind. Denies with a JSON permissionDecision whose reason
              names the exact command to run.
session-start SessionStart (startup|clear|compact): prints `status` so the orchestrator wakes
              up with the live state in context; silent when there is no `.ai-team/`.
"""

import json
import sys

from ai_team.machine import AGENT_KINDS, Machine
from ai_team.store import MachineError, Store, find_root, launcher


def _deny(reason):
    return json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }})


ORDER = ("You (the orchestrator) run these commands yourself with Bash, now and in this order; "
         "do not report them to the user and do not ask the user to run them.")


def _acquire_hint(machine, task, kinds, bin_):
    current = machine.current_phase(task)
    commands = []
    for kind in kinds:
        if kind in ("implementer", "reviewer", "security-audit") and current is not None:
            commands.append("%s acquire %s --phase %d" % (bin_, kind, current["n"]))
        else:
            commands.append("%s acquire %s" % (bin_, kind))
    return " or ".join("`%s`" % c for c in commands)


def pre_tool_use(payload):
    """Return (exit_code, stdout, stderr)."""
    if payload.get("tool_name") != "Agent":
        return 0, "", ""
    tool_input = payload.get("tool_input") or {}
    agent = tool_input.get("subagent_type") if isinstance(tool_input, dict) else None
    if not isinstance(agent, str) or not agent.startswith("organic-"):
        return 0, "", ""
    root = find_root(payload.get("cwd") or ".")
    if root is None:
        return 0, "", ""
    store = Store(root)
    machine = Machine(store)
    kinds = AGENT_KINDS.get(agent, ())
    if not kinds:
        return 0, "", ""
    task = store.current()
    candidates = [task] if task is not None else []
    if "retro" in kinds:
        candidates += [t for t in store.list_tasks() if t["status"] == "done"]
    for candidate in candidates:
        for ticket in machine.open_tickets(candidate):
            if ticket["kind"] in kinds:
                return 0, "", ""
    bin_ = launcher()
    if task is None and "retro" not in kinds:
        return 0, _deny(
            "ai-team: no task in progress under %s -- a sub-agent launch needs a ticket. %s Bounded change: "
            "`%s new <slug> --kind bounded` then `%s plan generate --objective ... --decision ... --check ... --file ...`; "
            "large change: `%s new <slug> --kind large` and follow `%s status`. Then `%s acquire %s` and relaunch the sub-agent."
            % (root, ORDER, bin_, bin_, bin_, bin_, bin_, " | ".join(kinds))
        ), ""
    if task is None:
        return 0, _deny("ai-team: no closed task to run a retro on. %s `%s close` first, then `%s acquire retro`." % (ORDER, bin_, bin_)), ""
    return 0, _deny(
        "ai-team: no open ticket for %s on task %s. %s `%s status`, then %s; if it refuses, do what it names first, then relaunch the sub-agent."
        % (agent, task["task"], ORDER, bin_, _acquire_hint(machine, task, kinds, bin_))
    ), ""


def session_start(payload):
    root = find_root(payload.get("cwd") or ".")
    if root is None:
        return 0, "", ""
    store = Store(root)
    machine = Machine(store)
    task = store.current()
    text = machine.status_text(task)
    paused = store.paused()
    if paused:
        text += "\nPaused: %s" % ", ".join("%s (%s)" % (t["task"], t.get("pending_question") or "no question recorded") for t in paused)
    return 0, "ai-team status (SessionStart hook; run the machine as `%s <verb>`):\n%s\n" % (launcher(), text), ""


def run(event, stdin_text):
    try:
        payload = json.loads(stdin_text) if stdin_text.strip() else {}
    except ValueError:
        return 0, "", "ai-team hook: stdin is not JSON -- allowed\n"
    if not isinstance(payload, dict):
        return 0, "", ""
    try:
        if event == "pre-tool-use":
            return pre_tool_use(payload)
        if event == "session-start":
            return session_start(payload)
        return 0, "", "ai-team hook: unknown event %r\n" % event
    except MachineError as exc:
        return 0, "", "ai-team hook: %s -- allowed\n" % exc
    except Exception as exc:  # noqa: BLE001 -- fail open
        return 0, "", "ai-team hook: %s: %s -- allowed\n" % (type(exc).__name__, exc)


def main(event):
    code, out, err = run(event, sys.stdin.read())
    if out:
        sys.stdout.write(out)
    if err:
        sys.stderr.write(err)
    return code
