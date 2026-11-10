"""`ai-team summary`: what the recorded tasks of a project add up to. Reads the task JSONs and
returns text; it writes nothing. A figure the JSON does not hold (a null, an absent key) is
`not recorded` and never adds as zero; the tokens and the duration of a resumed implementer
(attempts 2-4) are cumulative over the attempts before them, so they are listed apart and stay
out of every mean and total (machine.md, Verbs)."""

from ai_team.machine import OUTCOMES, RESUME_ATTEMPTS, TICKET_KINDS

NOT_RECORDED = "not recorded"
NO_TASK_LINE = "no recorded task under .ai-team/tasks -- nothing to summarize"


def _plural(count, noun):
    return "%d %s%s" % (count, noun, "" if count == 1 else "s")


def _is_resumed_implementer(ticket):
    return ticket["kind"] == "implementer" and ticket.get("attempt") in RESUME_ATTEMPTS


def _settled(tasks):
    return [t for task in tasks for t in task["tickets"] if t.get("settled_at") is not None]


def _figures_of(tickets, key):
    """The figures the tickets hold under `key`; a ticket without one contributes nothing."""
    return [t[key] for t in tickets if t.get(key) is not None]


def _describe_figures(values, counted, unit=""):
    """`mean 1500 · total 3000`, with `(k of n recorded)` when some tickets hold no figure."""
    if not values:
        return NOT_RECORDED
    text = "mean %d%s · total %d%s" % (round(sum(values) / len(values)), unit, sum(values), unit)
    if len(values) < counted:
        text += " (%d of %d recorded)" % (len(values), counted)
    return text


def _describe_outcomes(tickets):
    counts = {}
    for ticket in tickets:
        outcome = ticket.get("outcome") or NOT_RECORDED
        counts[outcome] = counts.get(outcome, 0) + 1
    known = [o for o in OUTCOMES if o in counts]
    extra = sorted(o for o in counts if o not in OUTCOMES)
    return ", ".join("%s %d" % (o, counts[o]) for o in known + extra)


def _figure_or_not_recorded(ticket, key, unit=""):
    value = ticket.get(key)
    return NOT_RECORDED if value is None else "%d%s" % (value, unit)


def _describe_resumed(ticket):
    return "tokens %s, duration %s" % (
        _figure_or_not_recorded(ticket, "tokens"), _figure_or_not_recorded(ticket, "duration_s", "s"))


def _kind_lines(tickets):
    lines = []
    for kind in TICKET_KINDS:
        of_kind = [t for t in tickets if t["kind"] == kind]
        if not of_kind:
            continue
        fresh = [t for t in of_kind if not _is_resumed_implementer(t)]
        lines.append("%-24s %4d  %s | duration: %s | tokens: %s" % (
            kind, len(of_kind), _describe_outcomes(of_kind),
            _describe_figures(_figures_of(fresh, "duration_s"), len(fresh), "s"),
            _describe_figures(_figures_of(fresh, "tokens"), len(fresh))))
    resumed = [t for t in tickets if _is_resumed_implementer(t)]
    if resumed:
        lines.append("resumed implementer      %s, tokens and duration cumulative per ticket, outside every mean and total above: %s"
                     % (_plural(len(resumed), "ticket"), "; ".join(_describe_resumed(t) for t in resumed)))
    return lines


def _task_lines(task):
    lines = ["%s (%s, %s)" % (task["task"], task.get("kind", NOT_RECORDED), task.get("status", NOT_RECORDED))]
    if not task["phases"]:
        lines.append("  no phase planned")
    for phase in task["phases"]:
        attempts = phase.get("attempts")
        shown = "attempts %s" % NOT_RECORDED if attempts is None else _plural(attempts, "attempt")
        lines.append("  phase %s: %s -- %s" % (phase.get("n"), shown, phase.get("title", "")))
    return lines


def _most_other_than_ok(tickets):
    """The ticket kinds with the most settled tickets whose outcome is not `ok`, with that count."""
    counts = {kind: sum(1 for t in tickets if t["kind"] == kind and t.get("outcome") != "ok") for kind in TICKET_KINDS}
    most = max(counts.values())
    if most == 0:
        return [], 0
    return [kind for kind in TICKET_KINDS if counts[kind] == most], most


def _verdict_line(tickets):
    kinds, count = _most_other_than_ok(tickets)
    if not kinds:
        return "Most outcomes other than ok: none -- no outcome other than ok among the settled tickets"
    each = " each" if len(kinds) > 1 else ""
    return "Most outcomes other than ok: %s (%d%s)" % (", ".join(kinds), count, each)


def recent_tasks(tasks, last=None):
    """The tasks oldest first; `last` keeps the N most recent by creation time (task id breaks ties)."""
    ordered = sorted(tasks, key=lambda t: (t.get("created_at") or "", t["task"]))
    return ordered[-last:] if last else ordered


def summarize(tasks, last=None):
    """The summary as a list of lines for the tasks of one project."""
    if not tasks:
        return [NO_TASK_LINE]
    chosen = recent_tasks(tasks, last)
    tickets = _settled(chosen)
    scope = "the last %d of %d" % (len(chosen), len(tasks)) if last and last < len(tasks) else "all"
    lines = ["ai-team summary -- %s (%s)" % (_plural(len(chosen), "task"), scope), "", "Settled tickets per kind"]
    lines += ["  " + line for line in _kind_lines(tickets)] or ["  no settled ticket"]
    lines += ["", "Tasks"]
    for task in chosen:
        lines += ["  " + line for line in _task_lines(task)]
    lines += ["", _verdict_line(tickets)]
    return lines
