"""Ticket conditions, attempts, settlement, commit gate, status. The judgment stays with the
orchestrator; what must always happen lives here (design note §8, §10, §13, §14).
"""

import os
import subprocess

from ai_team import debt, engram
from ai_team.design import load_design, set_frontmatter
from ai_team.receipt import derived_verdict, findings_of, validate_report
from ai_team.store import MachineError, utc_now

TICKET_KINDS = ("scout-map", "security-threat-model", "scout-scope", "implementer", "reviewer", "security-audit", "retro")
LENS_KINDS = ("reviewer", "security-audit")
OUTCOMES = ("ok", "warning", "needs_input", "blocked", "failed", "infra-death")
GOOD = ("ok", "warning")
MAX_ATTEMPTS = 6
RESUME_ATTEMPTS = (2, 3, 4)
FRESH_STRONGER_ATTEMPTS = (5, 6)
AGENT_KINDS = {
    "organic-scout": ("scout-map", "scout-scope"),
    "organic-security": ("security-threat-model", "security-audit"),
    "organic-implementer": ("implementer",),
    "organic-reviewer": ("reviewer",),
    "organic-retro": ("retro",),
}
CARDS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "cards")


def _int_field(name, value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MachineError("--%s must be a non-negative integer (got %r)" % (name, value), 2)
    return value


class Machine:
    def __init__(self, store):
        self.store = store

    # --- lookups -------------------------------------------------------------------
    def design_of(self, task):
        if not task.get("design"):
            return None
        path = self.store.abs(task["design"])
        if not os.path.isfile(path):
            return None
        return load_design(path)

    def phase(self, task, n):
        for phase in task["phases"]:
            if phase["n"] == n:
                return phase
        raise MachineError("task %s has no phase %s (phases: %s)" % (
            task["task"], n, ", ".join(str(p["n"]) for p in task["phases"]) or "none -- run `ai-team plan generate`"))

    def current_phase(self, task):
        for phase in task["phases"]:
            if phase["status"] != "committed":
                return phase
        return None

    def open_tickets(self, task):
        return [t for t in task["tickets"] if t["settled_at"] is None]

    def tickets(self, task, kind, phase=None, attempt=None, settled=None):
        out = []
        for ticket in task["tickets"]:
            if ticket["kind"] != kind:
                continue
            if phase is not None and ticket["phase"] != phase:
                continue
            if attempt is not None and ticket["attempt"] != attempt:
                continue
            if settled is True and ticket["settled_at"] is None:
                continue
            if settled is False and ticket["settled_at"] is not None:
                continue
            out.append(ticket)
        return out

    def ticket(self, task, ticket_id):
        for ticket in task["tickets"]:
            if ticket["id"] == ticket_id:
                return ticket
        raise MachineError("task %s has no ticket %s" % (task["task"], ticket_id))

    # --- conditions ----------------------------------------------------------------
    def conditions(self, task, kind, phase_n):
        """Every reason the ticket cannot be issued now; an empty list means allowed."""
        if kind not in TICKET_KINDS:
            return ["unknown ticket kind %r (kinds: %s)" % (kind, ", ".join(TICKET_KINDS))]
        missing = []
        if kind == "retro":
            if task["status"] != "done":
                missing.append("task is %s -- retro runs after `ai-team close`" % task["status"])
        elif task["status"] != "active":
            missing.append("task is %s -- `ai-team resume` first" % task["status"])

        opens = self.open_tickets(task)
        if kind == "scout-map":
            blocking = [t for t in opens if t["kind"] != "scout-map"]
        elif kind in LENS_KINDS:
            blocking = [t for t in opens if not (t["kind"] in LENS_KINDS and t["kind"] != kind and t["phase"] == phase_n)]
        else:
            blocking = opens
        for ticket in blocking:
            missing.append("ticket %s (%s) is open -- settle it first" % (ticket["id"], ticket["kind"]))

        design = self.design_of(task)
        if kind == "security-threat-model":
            if design is None:
                missing.append("no design file (task.design is %r)" % task.get("design"))
            else:
                if design["status"] == "approved":
                    missing.append("the design is already approved -- the threat-model runs on the draft")
                if design["security"] != "pending":
                    missing.append("design frontmatter says security: %s -- a threat-model needs security: pending" % design["security"])
        elif kind == "scout-scope":
            if design is None or design["status"] != "approved":
                missing.append("design must be approved (`ai-team design approve <path>`)")
        elif kind == "implementer":
            missing += self._implementer_conditions(task, design, phase_n)
        elif kind in LENS_KINDS:
            missing += self._lens_conditions(task, kind, phase_n)
        return missing

    def _implementer_conditions(self, task, design, phase_n):
        missing = []
        if task["kind"] == "large":
            if design is None or design["status"] != "approved":
                missing.append("large task: the design must be approved first")
            if not task.get("scope_report") and not task.get("scope_skipped"):
                missing.append("large task: settle a scout-scope ticket with --report, or `plan generate --scope-skipped \"<why>\"`")
        if not task.get("plan") or not task["phases"]:
            missing.append("no plan yet -- `ai-team plan generate`")
            return missing
        if phase_n is None:
            missing.append("--phase n is required")
            return missing
        try:
            phase = self.phase(task, phase_n)
        except MachineError as exc:
            return missing + [str(exc)]
        if phase["status"] == "committed":
            missing.append("phase %d is already committed" % phase_n)
        for earlier in task["phases"]:
            if earlier["n"] < phase_n and earlier["status"] != "committed":
                missing.append("phase %d is not committed yet -- phases are delivered in order" % earlier["n"])
        if phase["attempts"] >= MAX_ATTEMPTS:
            missing.append(
                "phase %d has used its %d attempts -- reopen the design (amend `%s`, `design approve`, `plan generate`)"
                % (phase_n, MAX_ATTEMPTS, task.get("design") or "the design")
            )
        return missing

    def _lens_conditions(self, task, kind, phase_n):
        missing = []
        if phase_n is None:
            return ["--phase n is required"]
        try:
            phase = self.phase(task, phase_n)
        except MachineError as exc:
            return [str(exc)]
        if phase["tier"] is None:
            missing.append("tier not declared for phase %d -- `ai-team tier --phase %d <0|1|2> --reason \"...\"`" % (phase_n, phase_n))
        elif phase["tier"] == 0:
            missing.append("phase %d is tier 0 -- no reviewer; run `ai-team commit-check --phase %d`" % (phase_n, phase_n))
        elif kind == "security-audit" and phase["tier"] != 2:
            missing.append("phase %d is tier %d -- security-audit runs at tier 2 only" % (phase_n, phase["tier"]))
        attempt = phase["attempts"]
        impl = self._latest(self.tickets(task, "implementer", phase_n, attempt, settled=True))
        if attempt == 0 or impl is None:
            missing.append("no settled implementer ticket for phase %d attempt %d" % (phase_n, attempt))
        elif impl["outcome"] not in GOOD:
            missing.append("implementer attempt %d settled %s -- a lens reviews an ok/warning candidate" % (attempt, impl["outcome"]))
        done = self._latest(self.tickets(task, kind, phase_n, attempt, settled=True))
        if done is not None and done["verdict"] is not None:
            missing.append("%s already settled for attempt %d (%s) -- next: `ai-team acquire implementer --phase %d` or `commit-check`"
                           % (kind, attempt, done["verdict"], phase_n))
        return missing

    @staticmethod
    def _latest(tickets):
        return tickets[-1] if tickets else None

    # --- verbs ---------------------------------------------------------------------
    def acquire(self, task, kind, phase_n):
        if kind in ("scout-map", "security-threat-model", "scout-scope", "retro"):
            phase_n = None
        elif phase_n is None:
            current = self.current_phase(task)
            phase_n = current["n"] if current else None
        missing = self.conditions(task, kind, phase_n)
        if missing:
            raise MachineError("acquire %s refused:\n  - %s" % (kind, "\n  - ".join(missing)))
        attempt = None
        if kind == "implementer":
            phase = self.phase(task, phase_n)
            phase["attempts"] += 1
            phase["status"] = "implementing"
            attempt = phase["attempts"]
        elif kind in LENS_KINDS:
            phase = self.phase(task, phase_n)
            phase["status"] = "reviewing"
            attempt = phase["attempts"]
        ticket = {
            "id": "t%d" % (len(task["tickets"]) + 1),
            "kind": kind,
            "phase": phase_n,
            "attempt": attempt,
            "issued_at": utc_now(),
            "settled_at": None,
            "outcome": None,
            "model": None,
            "tokens": None,
            "tool_uses": None,
            "duration_s": None,
            "report": None,
            "verdict": None,
            "findings": None,
            "deferred": [],
        }
        task["tickets"].append(ticket)
        self.store.save(task)
        return ticket

    def attempt_hint(self, kind, attempt):
        if kind != "implementer" or attempt is None:
            return None
        if attempt in RESUME_ATTEMPTS:
            return "attempt %d: resume the attempt-1 implementer (SendMessage) with the findings" % attempt
        if attempt in FRESH_STRONGER_ATTEMPTS:
            return "attempt %d: fresh implementer on the stronger model (opus)" % attempt
        return "attempt 1: fresh implementer (sonnet)"

    def settle(self, task, ticket_id, outcome, model=None, tokens=None, tool_uses=None,
               duration_s=None, report=None, defer=()):
        ticket = self.ticket(task, ticket_id)
        if ticket["settled_at"] is not None:
            raise MachineError("ticket %s was already settled at %s" % (ticket_id, ticket["settled_at"]))
        if outcome not in OUTCOMES:
            raise MachineError("--outcome must be one of %s (got %r)" % (", ".join(OUTCOMES), outcome), 2)
        if outcome != "infra-death":
            if not model:
                raise MachineError("--model is required (the harness reports it)", 2)
            tokens = _int_field("tokens", tokens)
            tool_uses = _int_field("tool-uses", tool_uses)
            duration_s = _int_field("duration", duration_s)
        kind = ticket["kind"]
        data = None
        notes = []
        report_rel = None
        if report:
            report_rel = self.store.rel(report)
            if not self.store.contained(report_rel) or not os.path.isfile(self.store.abs(report_rel)):
                raise MachineError("--report %s must be an existing file inside the project" % report_rel)
        elif kind in LENS_KINDS + ("scout-scope",) and outcome in GOOD:
            raise MachineError("a %s ticket settled %s needs --report <path.md>" % (kind, outcome))
        if kind in LENS_KINDS and report_rel:
            code, out, err, data = validate_report(self.store.abs(report_rel), self.store.root)
            if code != 0:
                raise MachineError("report %s does not validate -- the ticket stays open, relaunch the lens:\n%s"
                                   % (report_rel, "\n".join(out + err)), code)
            is_fragment = data.get("kind") == "security-fragment"
            if kind == "reviewer" and is_fragment:
                raise MachineError("a reviewer report must carry a full receipt, not a security fragment")
            if kind == "security-audit" and not is_fragment:
                raise MachineError('a security-audit report must carry a fragment (kind: "security-fragment")')
            ticket["verdict"] = derived_verdict(data)
            ticket["findings"] = findings_of(data)
            notes += out
        if kind == "scout-scope" and outcome in GOOD:
            task["scope_report"] = report_rel
            task["scope_skipped"] = None
        if kind == "security-threat-model" and outcome in GOOD and task.get("design"):
            set_frontmatter(self.store.abs(task["design"]), {"security": "done"})
            notes.append("design frontmatter: security: done")
        if kind == "implementer" and outcome == "infra-death":
            self.phase(task, ticket["phase"])["attempts"] -= 1
            notes.append("infra-death does not count as an attempt")
        ticket.update({
            "settled_at": utc_now(), "outcome": outcome, "model": model, "tokens": tokens,
            "tool_uses": tool_uses, "duration_s": duration_s, "report": report_rel,
        })
        if defer:
            if not ticket["findings"]:
                raise MachineError("--defer needs a lens ticket with a validated receipt")
            known = {f["id"]: f for f in ticket["findings"]}
            unknown = [d for d in defer if d not in known]
            if unknown:
                raise MachineError("--defer names findings not in the receipt: %s" % ", ".join(unknown))
            rows = debt.append_findings(os.path.join(self.store.ai_team, "tech-debt.md"), report_rel, [known[d] for d in defer])
            ticket["deferred"] = list(defer)
            notes.append("%d row(s) appended to .ai-team/tech-debt.md" % rows)
            engram.mirror(
                "ai-team debt: %s" % task["task"],
                "Deferred %s from %s (task %s)" % (", ".join(defer), report_rel, task["task"]),
                "decision", self.store.root,
            )
        self.store.save(task)
        return ticket, notes

    def declare_tier(self, task, phase_n, tier, reason):
        if tier not in (0, 1, 2):
            raise MachineError("tier must be 0, 1 or 2", 2)
        if not reason or not reason.strip():
            raise MachineError("--reason is required: review cost is never unexplained", 2)
        phase = self.phase(task, phase_n)
        impl = self._latest(self.tickets(task, "implementer", phase_n, phase["attempts"], settled=True))
        if impl is None:
            raise MachineError("tier is decided from the candidate's diff -- settle the implementer ticket of phase %d first" % phase_n)
        phase["tier"] = tier
        phase["tier_reason"] = reason.strip()
        self.store.save(task)
        return phase

    def ruling(self, task, ticket_id, finding, text, cost_if_wrong):
        ticket = self.ticket(task, ticket_id)
        if ticket["settled_at"] is None or not ticket["findings"]:
            raise MachineError("ticket %s is not a settled lens ticket with findings" % ticket_id)
        ids = {f["id"] for f in ticket["findings"]}
        if finding not in ids:
            raise MachineError("ticket %s has no finding %s (findings: %s)" % (ticket_id, finding, ", ".join(sorted(ids))))
        if not text or not cost_if_wrong:
            raise MachineError("--text and --cost-if-wrong are both required", 2)
        entry = {"at": utc_now(), "ticket": ticket_id, "finding": finding, "text": text, "cost_if_wrong": cost_if_wrong}
        task["rulings"].append(entry)
        self.store.save(task)
        return entry

    def _ruled(self, task, ticket_id):
        return {r["finding"] for r in task["rulings"] if r["ticket"] == ticket_id}

    def _lens_gate(self, task, kind, phase):
        reasons = []
        ticket = self._latest(self.tickets(task, kind, phase["n"], phase["attempts"], settled=True))
        if ticket is None:
            return ["no settled %s ticket for attempt %d" % (kind, phase["attempts"])]
        if ticket["outcome"] not in GOOD or not ticket["report"]:
            return ["%s %s settled %s without a report" % (kind, ticket["id"], ticket["outcome"])]
        code, out, err, data = validate_report(self.store.abs(ticket["report"]), self.store.root)
        if code != 0:
            return ["%s report %s no longer validates: %s" % (kind, ticket["report"], "; ".join(out + err))]
        if derived_verdict(data) == "review-blocked":
            ruled = self._ruled(task, ticket["id"])
            unruled = [f["id"] for f in findings_of(data) if f["severity"] == "CRITICAL" and f["id"] not in ruled]
            if unruled:
                reasons.append("%s %s is review-blocked: CRITICAL %s without a ruling (`ai-team ruling %s --finding <id> ...`)"
                               % (kind, ticket["id"], ", ".join(unruled), ticket["id"]))
        return reasons

    def commit_check(self, task, phase_n):
        phase = self.phase(task, phase_n)
        reasons = []
        if phase["status"] == "committed":
            return False, ["phase %d is already committed (%s)" % (phase_n, phase["commit"])]
        for ticket in self.open_tickets(task):
            if ticket["phase"] == phase_n:
                reasons.append("ticket %s (%s) is still open" % (ticket["id"], ticket["kind"]))
        impl = self._latest(self.tickets(task, "implementer", phase_n, phase["attempts"], settled=True))
        if phase["attempts"] == 0 or impl is None:
            reasons.append("no settled implementer ticket for phase %d" % phase_n)
        elif impl["outcome"] not in GOOD:
            reasons.append("implementer attempt %d settled %s" % (phase["attempts"], impl["outcome"]))
        if phase["tier"] is None:
            reasons.append("tier not declared -- `ai-team tier --phase %d <0|1|2> --reason \"...\"`" % phase_n)
        else:
            if phase["tier"] >= 1:
                reasons += self._lens_gate(task, "reviewer", phase)
            if phase["tier"] == 2:
                reasons += self._lens_gate(task, "security-audit", phase)
        return (not reasons), reasons

    def phase_done(self, task, phase_n, commit):
        ok, reasons = self.commit_check(task, phase_n)
        if not ok:
            raise MachineError("phase %d may not be recorded as committed:\n  - %s" % (phase_n, "\n  - ".join(reasons)))
        completed = subprocess.run(
            ["git", "-C", self.store.root, "rev-parse", "--verify", "--quiet", "%s^{commit}" % commit],
            capture_output=True, text=True, check=False,
        )
        if completed.returncode != 0:
            raise MachineError("commit %r not found in %s" % (commit, self.store.root))
        phase = self.phase(task, phase_n)
        phase["commit"] = completed.stdout.strip()
        phase["status"] = "committed"
        self.store.save(task)
        return phase

    def close(self, task):
        if task["status"] != "active":
            raise MachineError("task %s is %s" % (task["task"], task["status"]))
        if not task["phases"]:
            raise MachineError("task %s has no phases -- nothing was planned" % task["task"])
        pending = [p["n"] for p in task["phases"] if p["status"] != "committed"]
        if pending:
            raise MachineError("phases not committed: %s" % ", ".join(str(n) for n in pending))
        if self.open_tickets(task):
            raise MachineError("open tickets: %s" % ", ".join(t["id"] for t in self.open_tickets(task)))
        task["status"] = "done"
        task["closed_at"] = utc_now()
        self.store.save(task)
        balance = self.balance(task)
        engram.mirror(
            "ai-team task closed: %s" % task["task"],
            "kind %s · %d phases · %d tickets · %s tokens · %d attempts · commits %s" % (
                task["kind"], len(task["phases"]), balance["tickets"], balance["tokens"],
                balance["attempts"], ", ".join(p["commit"][:10] for p in task["phases"])),
            "decision", self.store.root,
        )
        return balance

    def pause(self, task, question):
        if task["status"] != "active":
            raise MachineError("task %s is %s" % (task["task"], task["status"]))
        task["status"] = "paused"
        task["pending_question"] = question
        self.store.save(task)

    def resume(self, task):
        if task["status"] != "paused":
            raise MachineError("task %s is %s, not paused" % (task["task"], task["status"]))
        if self.store.current() is not None:
            raise MachineError("task %s is active -- one active task at a time" % self.store.current()["task"])
        task["status"] = "active"
        task["pending_question"] = None
        self.store.save(task)

    # --- views ---------------------------------------------------------------------
    def balance(self, task):
        settled = [t for t in task["tickets"] if t["settled_at"] is not None]
        per_kind = {}
        for ticket in settled:
            per_kind[ticket["kind"]] = per_kind.get(ticket["kind"], 0) + 1
        return {
            "tickets": len(settled),
            "tokens": sum(t["tokens"] or 0 for t in settled),
            "tool_uses": sum(t["tool_uses"] or 0 for t in settled),
            "duration_s": sum(t["duration_s"] or 0 for t in settled),
            "attempts": sum(p["attempts"] for p in task["phases"]),
            "per_kind": per_kind,
            "outcomes": {o: sum(1 for t in settled if t["outcome"] == o) for o in OUTCOMES if any(t["outcome"] == o for t in settled)},
        }

    def findings_trend(self, task, phase):
        """Finding counts per attempt from the reviewer receipts; a non-decreasing step is a warning."""
        counts = []
        for attempt in range(1, phase["attempts"] + 1):
            ticket = self._latest(self.tickets(task, "reviewer", phase["n"], attempt, settled=True))
            if ticket is not None and ticket["findings"] is not None:
                counts.append((attempt, len(ticket["findings"])))
        warnings = []
        for (a1, c1), (a2, c2) in zip(counts, counts[1:]):
            if c2 >= c1 and c1 > 0:
                warnings.append("findings did not decrease between attempts %d (%d) and %d (%d) -- the fix class is wrong: reopen the design" % (a1, c1, a2, c2))
        return counts, warnings

    def allowed_now(self, task):
        allowed = []
        denied = []
        current = self.current_phase(task)
        phase_n = current["n"] if current else None
        for kind in TICKET_KINDS:
            n = phase_n if kind in ("implementer",) + LENS_KINDS else None
            missing = self.conditions(task, kind, n)
            label = kind + (" --phase %d" % n if n is not None else "")
            if missing:
                denied.append((label, missing[0]))
            else:
                hint = ""
                if kind == "implementer" and current is not None:
                    hint = " (%s)" % self.attempt_hint(kind, current["attempts"] + 1)
                allowed.append("acquire %s%s" % (label, hint))
        for ticket in self.open_tickets(task):
            allowed.append("settle %s" % ticket["id"])
        if current is not None:
            ok, _ = self.commit_check(task, phase_n)
            if ok:
                allowed.append("commit-check --phase %d → git commit → phase done %d --commit <hash>" % (phase_n, phase_n))
        elif task["phases"] and task["status"] == "active":
            allowed.append("close")
        return allowed, denied

    def moment(self, task):
        if task is None:
            return "classify"
        if task["status"] == "done":
            return "close"
        design = self.design_of(task)
        if task["kind"] == "large" and (design is None or design["status"] != "approved"):
            return "design"
        if not task["phases"]:
            return "plan"
        current = self.current_phase(task)
        if current is None:
            return "close"
        if self.open_tickets(task):
            return "ingest"
        impl = self._latest(self.tickets(task, "implementer", current["n"], current["attempts"], settled=True))
        if current["attempts"] == 0 or impl is None:
            return "delegate"
        if impl["outcome"] not in GOOD:
            return "delegate"
        ok, _ = self.commit_check(task, current["n"])
        if ok:
            return "commit"
        return "review"

    def card_path(self, name):
        return os.path.join(CARDS_DIR, name + ".md")

    def status_json(self, task):
        design = self.design_of(task)
        current = self.current_phase(task)
        allowed, denied = self.allowed_now(task)
        warnings = []
        if current is not None:
            _, warnings = self.findings_trend(task, current)
        return {
            "task": task["task"], "kind": task["kind"], "status": task["status"],
            "pending_question": task.get("pending_question"),
            "design": {"path": task.get("design"), "status": design["status"] if design else None,
                       "security": design["security"] if design else None},
            "plan": task.get("plan"), "scope_report": task.get("scope_report"), "scope_skipped": task.get("scope_skipped"),
            "phases": task["phases"], "current_phase": current["n"] if current else None,
            "open_tickets": self.open_tickets(task), "allowed": allowed, "denied": denied,
            "warnings": warnings, "balance": self.balance(task),
            "moment": self.moment(task), "card": self.card_path(self.moment(task)),
        }

    def status_text(self, task):
        if task is None:
            return "ai-team: no task in progress. Classify the request aloud: question · bounded change · large change.\nCard: classify → %s" % self.card_path("classify")
        view = self.status_json(task)
        design = view["design"]
        lines = ["Task: %s (%s, %s)" % (view["task"], view["kind"], view["status"])]
        if view["pending_question"]:
            lines[-1] += " · pending question: %s" % view["pending_question"]
        design_text = "none" if not design["path"] else (design["status"] or "unreadable")
        if design["security"]:
            design_text += ", security %s" % design["security"]
        plan_text = "%d phases" % len(task["phases"]) if task["phases"] else "none"
        if task["kind"] == "bounded":
            scope_text = "n/a (bounded)"
        elif view["scope_report"]:
            scope_text = "report %s" % view["scope_report"]
        elif view["scope_skipped"]:
            scope_text = "skipped: %s" % view["scope_skipped"]
        else:
            scope_text = "missing"

        lines.append("Design: %s · Plan: %s · Scope: %s" % (design_text, plan_text, scope_text))
        current = self.current_phase(task)
        if current is not None:
            phase_line = 'Phase %d/%d "%s": %s · attempts %d/%d' % (
                current["n"], len(task["phases"]), current["title"], current["status"], current["attempts"], MAX_ATTEMPTS)
            if current["tier"] is not None:
                phase_line += " · tier %d (%s)" % (current["tier"], current["tier_reason"])
            lines.append(phase_line)
        elif task["phases"]:
            lines.append("Phases: %d/%d committed" % (len(task["phases"]), len(task["phases"])))
        for ticket in view["open_tickets"]:
            extra = "" if ticket["phase"] is None else ", phase %d, attempt %s" % (ticket["phase"], ticket["attempt"])
            lines.append("Open: %s (%s%s) since %s" % (ticket["id"], ticket["kind"], extra, ticket["issued_at"][11:]))
        for warning in view["warnings"]:
            lines.append("Warning: %s" % warning)
        lines.append("Allowed now: %s" % (" · ".join(view["allowed"]) or "nothing"))
        if view["denied"]:
            lines.append("Denied: %s" % " · ".join("%s (%s)" % (label, reason) for label, reason in view["denied"]))
        balance = view["balance"]
        lines.append("Balance: %d tickets settled · %d tokens · %d tool uses · %ds" % (
            balance["tickets"], balance["tokens"], balance["tool_uses"], balance["duration_s"]))
        lines.append("Card: %s → %s" % (view["moment"], view["card"]))
        return "\n".join(lines)
