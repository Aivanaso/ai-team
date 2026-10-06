"""Ticket conditions, attempts, settlement, commit gate, status. The judgment stays with the
orchestrator; what must always happen lives here (design note §8, §10, §13, §14).
"""

import os
import subprocess
import unicodedata

from ai_team import debt, engram, worktree
from ai_team.design import load_design, set_frontmatter
from ai_team.plan import load_plan, load_scope_report, phase_of
from ai_team.receipt import closed_of, derived_verdict, findings_of, validate_report
from ai_team.store import MachineError, utc_now

TICKET_KINDS = ("scout-map", "security-threat-model", "scout-scope", "implementer", "reviewer", "security-audit", "retro")
LENS_KINDS = ("reviewer", "security-audit")
SEVERITY_RANK = {"MINOR": 0, "MAJOR": 1, "CRITICAL": 2}
GATED_SEVERITIES = ("MAJOR", "CRITICAL")
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


def _nfc(value):
    return unicodedata.normalize("NFC", value) if isinstance(value, str) else value


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
        else:
            # one ticket at a time -- the two review lenses included: they audit one working
            # tree, and a mutation probe by one is a phantom defect for the other
            blocking = opens
        for ticket in blocking:
            missing.append("ticket %s (%s) is open -- settle it first" % (ticket["id"], ticket["kind"]))

        design = self.design_of(task)
        if kind == "security-threat-model":
            if design is None:
                missing.append("no design file (task.design is %r) -- `ai-team design attach <path>` records the draft design" % task.get("design"))
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
        return missing + self._calibrated_check_conditions(task, phase_n)

    def _calibrated_check_conditions(self, task, phase_n):
        """A phase reaches an implementer only with at least one calibrated acceptance check:
        a phase whose every check was demoted to an open question would settle `ok` having
        verified nothing."""
        try:
            phase = phase_of(load_plan(self.store.abs(task["plan"])), phase_n)
        except MachineError as exc:
            return [str(exc)]
        if phase["acceptance_checks"]:
            return []
        demoted = [q for q in phase["open_questions"] if q.startswith("not calibrated:")]
        return [
            "phase %d has no calibrated acceptance check -- %s. Run one yourself and record it: "
            "`ai-team plan amend --phase %d --reason \"...\" --check \"<cmd>\" --failure \"<how it fails>\"`"
            % (phase_n, "; ".join(demoted) if demoted else "the plan declares none", phase_n)
        ]

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

    def _tree_unchanged_since_implementer(self, task, ticket, tree):
        """A lens settles on the tree the implementer settled: the fingerprint recorded on the
        implementer ticket of the same attempt must match the tree now."""
        impl = self._latest(self.tickets(task, "implementer", ticket["phase"], ticket["attempt"], settled=True))
        if impl is None or not impl.get("tree") or tree is None or impl["tree"] == tree:
            return
        changed = worktree.changed_between(self.store.root, impl["tree"], tree)
        restore = worktree.restore_commands(impl["tree"], changed)
        raise MachineError(
            "the working tree changed while ticket %s was open -- %s. A lens leaves the tree exactly as the "
            "implementer settled it (a mutation probe ends with a byte-for-byte restore). The ticket stays open; "
            "restore, then settle again:\n  %s"
            % (ticket["id"], "; ".join(changed) if changed else "paths unknown",
               "\n  ".join(restore) if restore else "(git could not name the paths: compare against `git status`)"))

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
            "tree": None,
        }
        task["tickets"].append(ticket)
        self.store.save(task)
        return ticket

    def attempt_hint(self, task, ticket):
        """The line printed under an issued ticket: how this attempt is launched."""
        kind, attempt = ticket["kind"], ticket["attempt"]
        if attempt is None:
            return None
        if kind == "implementer":
            if attempt in RESUME_ATTEMPTS:
                return "attempt %d: resume the attempt-1 implementer (SendMessage) with the findings" % attempt
            if attempt in FRESH_STRONGER_ATTEMPTS:
                return "attempt %d: fresh implementer on the stronger model (opus)" % attempt
            return "attempt 1: fresh implementer (sonnet)"
        if kind in LENS_KINDS and attempt >= 2:
            return self._lens_prior_hint(task, kind, ticket["phase"], attempt)
        return None

    def _prior_lens_ticket(self, task, kind, phase_n, attempt):
        """The latest settled ticket of this lens kind and phase, from an earlier attempt, that
        carries a validated report -- skipping a report-less settlement (blocked/failed before
        reaching review). Shared by the attempt hint and the `closed` reconciliation (security
        MUST F-5: both read the same source)."""
        earlier = [t for t in self.tickets(task, kind, phase_n, settled=True) if t["attempt"] < attempt and t.get("report")]
        return earlier[-1] if earlier else None

    def _lens_prior_hint(self, task, kind, phase_n, attempt):
        """Attempt ≥ 2 of a lens is a delta pass over the earlier report -- when one exists. An
        earlier attempt that settled before reaching review left none, and the lens runs a full
        pass with `prior_report: none` instead of deducing that from an absent path."""
        prior = self._prior_lens_ticket(task, kind, phase_n, attempt)
        if prior is not None:
            return "attempt %d: delta pass -- inject prior_report %s and its delta_scope" % (attempt, prior["report"])
        impls = [t for t in self.tickets(task, "implementer", phase_n, settled=True) if t["attempt"] < attempt]
        why = "; ".join("attempt %d settled %s" % (t["attempt"], t["outcome"]) for t in impls) or "no earlier attempt reached review"
        return "attempt %d: full pass -- no earlier %s report exists for this phase (%s); inject prior_report: none" % (attempt, kind, why)

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
        tree = None
        if kind == "implementer" or kind in LENS_KINDS:
            tree = worktree.fingerprint(self.store.root)
        if kind in LENS_KINDS:
            self._tree_unchanged_since_implementer(task, ticket, tree)
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
            notes += self._reconcile_closed(task, ticket, kind, data)
            notes += out
        if kind == "scout-scope" and outcome in GOOD:
            try:
                load_scope_report(self.store.abs(report_rel))
            except MachineError as exc:
                raise MachineError("%s\n-- the ticket stays open, relaunch the scout with these lines" % exc)
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
            "tool_uses": tool_uses, "duration_s": duration_s, "report": report_rel, "tree": tree,
        })
        if defer:
            if not ticket["findings"]:
                raise MachineError("--defer needs a lens ticket with a validated receipt")
            known = {f["id"]: f for f in ticket["findings"]}
            unknown = [d for d in defer if d not in known]
            if unknown:
                raise MachineError("--defer names findings not in the receipt: %s" % ", ".join(unknown))
            critical = [d for d in defer if known[d]["severity"] == "CRITICAL"]
            if critical:
                raise MachineError(
                    "--defer refuses CRITICAL %s -- a CRITICAL finding is ruled, never deferred: "
                    "`ai-team ruling %s --finding %s --text \"...\" --cost-if-wrong \"...\"`"
                    % (", ".join(critical), ticket_id, critical[0])
                )
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

    def _dispositions(self, task, kind, phase_n):
        """Every ruling or deferral recorded against a settled ticket of this kind and phase,
        resolved through that ticket's OWN findings snapshot to (NFC id, NFC file, severity,
        is_ruling) -- the identity a later finding of the same id is checked against
        (security MUST F-1: file must match and the later severity must not be higher)."""
        out = []
        for ticket in self.tickets(task, kind, phase_n, settled=True):
            by_id = {f["id"]: f for f in (ticket.get("findings") or [])}
            for finding_id in self._ruled(task, ticket["id"]):
                found = by_id.get(finding_id)
                if found:
                    out.append((_nfc(found["id"]), _nfc(found["file"]), found["severity"], True))
            for finding_id in ticket.get("deferred") or []:
                found = by_id.get(finding_id)
                if found:
                    out.append((_nfc(found["id"]), _nfc(found["file"]), found["severity"], False))
        return out

    @staticmethod
    def _dispositioned(dispositions, finding):
        """A disposition satisfies `finding` only when its id and file (NFC) match and its
        severity is not lower than the finding's; a CRITICAL is satisfied by a ruling only,
        since a deferral on a CRITICAL is refused at settle and never reaches this list."""
        fid, ffile, frank = _nfc(finding["id"]), _nfc(finding["file"]), SEVERITY_RANK[finding["severity"]]
        for did, dfile, dseverity, is_ruling in dispositions:
            if did != fid or dfile != ffile or SEVERITY_RANK[dseverity] < frank:
                continue
            if finding["severity"] == "CRITICAL" and not is_ruling:
                continue
            return True
        return False

    def _unaccounted_reason(self, ticket_id, prior_id, finding):
        """One line per prior MAJOR/CRITICAL a delta receipt drops without accounting for it --
        the three ways that actually settle this ticket (a CRITICAL is never deferred)."""
        options = ["re-list %s under findings" % finding["id"]]
        if finding["severity"] == "MAJOR":
            options[0] += " (then `ai-team settle %s --defer %s` if it stays)" % (ticket_id, finding["id"])
        options.append("add it to closed: [{\"id\": %r, \"file\": ..., \"line\": ...}]" % finding["id"])
        options.append('`ai-team ruling %s --finding %s --text "..." --cost-if-wrong "..."`' % (prior_id, finding["id"]))
        disposed_how = "closed nor ruled" if finding["severity"] == "CRITICAL" else "closed, ruled nor deferred"
        return "%s (%s, from %s) is neither re-listed, %s -- %s" % (
            finding["id"], finding["severity"], prior_id, disposed_how, ", ".join(options)
        )

    def _reconcile_closed(self, task, ticket, kind, data):
        """A delta pass (attempt >= 2) accounts for every MAJOR/CRITICAL the prior settled lens
        ticket of the same kind and phase reported: re-listed under `findings`, closed with a
        citation, or already ruled/deferred (`_dispositioned`, which matches by id, file and
        severity). `closed` is for a delta pass only -- settle owns this discriminator (open
        question resolved 2026-09-20T19:03:49Z), not `receipt.py`, which stays ticket-free.
        Returns the notes to print; raises on refusal (before any write)."""
        closed = closed_of(data)
        if ticket["attempt"] < 2:
            if closed:
                raise MachineError(
                    "ticket %s is attempt %d -- closed is for a delta pass (attempt >= 2 of the same "
                    "lens kind and phase); a fresh attempt reports findings only" % (ticket["id"], ticket["attempt"])
                )
            return []
        prior = self._prior_lens_ticket(task, kind, ticket["phase"], ticket["attempt"])
        if prior is None:
            # No earlier report-carrying ticket of this lens kind and phase exists: this
            # settles as a full pass in effect (nothing to reconcile against), the same as an
            # attempt-1 ticket -- `closed` names nothing real and is refused identically.
            if closed:
                raise MachineError(
                    "ticket %s: closed names id(s) but no earlier %s report exists for phase %d -- "
                    "this settles as a full pass (nothing to reconcile `closed` against); relist "
                    "under findings instead" % (ticket["id"], kind, ticket["phase"])
                )
            return ["ticket %s: no earlier settled %s report for phase %d -- closed reconciliation "
                    "did not run (this settles as a full pass)" % (ticket["id"], kind, ticket["phase"])]
        prior_findings = {f["id"]: f for f in (prior.get("findings") or [])}
        prior_ids_nfc = {_nfc(fid) for fid in prior_findings}
        unknown = sorted({c["id"] for c in closed if c.get("id") and _nfc(c["id"]) not in prior_ids_nfc})
        if unknown:
            raise MachineError(
                "ticket %s: closed names id(s) %s not reported by %s -- closed accounts for a prior "
                "finding, it does not introduce one" % (ticket["id"], ", ".join(unknown), prior["id"])
            )
        closed_ids_nfc = {_nfc(c["id"]) for c in closed if c.get("id")}
        current_ids_nfc = {_nfc(f["id"]) for f in ticket["findings"]}
        dispositions = self._dispositions(task, kind, ticket["phase"])
        unresolved = [
            f for fid, f in prior_findings.items()
            if f["severity"] in GATED_SEVERITIES
            and _nfc(fid) not in current_ids_nfc
            and _nfc(fid) not in closed_ids_nfc
            and not self._dispositioned(dispositions, f)
        ]
        if unresolved:
            reasons = [self._unaccounted_reason(ticket["id"], prior["id"], f) for f in unresolved]
            raise MachineError(
                "ticket %s does not account for every MAJOR/CRITICAL finding of %s:\n  - %s"
                % (ticket["id"], prior["id"], "\n  - ".join(reasons))
            )
        return []

    def _lens_gate(self, task, kind, phase):
        ticket = self._latest(self.tickets(task, kind, phase["n"], phase["attempts"], settled=True))
        if ticket is None:
            return ["no settled %s ticket for attempt %d" % (kind, phase["attempts"])]
        if ticket["outcome"] not in GOOD or not ticket["report"]:
            return ["%s %s settled %s without a report" % (kind, ticket["id"], ticket["outcome"])]
        code, out, err, data = validate_report(self.store.abs(ticket["report"]), self.store.root)
        if code != 0:
            return ["%s report %s no longer validates: %s" % (kind, ticket["report"], "; ".join(out + err))]
        live_verdict = derived_verdict(data)
        live_findings = findings_of(data)
        if live_verdict != ticket["verdict"] or live_findings != ticket["findings"]:
            return ["%s report %s differs from the findings/verdict snapshot recorded at settle for ticket %s "
                     "-- restore the report to the content it had at settle, or open the next attempt "
                     "(`ai-team acquire implementer --phase %d`) and review again"
                     % (kind, ticket["report"], ticket["id"], phase["n"])]
        dispositions = self._dispositions(task, kind, phase["n"])
        reasons = []
        for f in live_findings:
            if f["severity"] not in GATED_SEVERITIES or self._dispositioned(dispositions, f):
                continue
            if f["severity"] == "CRITICAL":
                reasons.append(
                    "%s %s CRITICAL %s without a ruling (`ai-team ruling %s --finding %s --text \"...\" "
                    "--cost-if-wrong \"...\"`)" % (kind, ticket["id"], f["id"], ticket["id"], f["id"])
                )
            else:
                reasons.append(
                    "%s %s MAJOR %s without a ruling or a deferral (`ai-team ruling %s --finding %s --text \"...\" "
                    "--cost-if-wrong \"...\"` or `ai-team settle %s --defer %s`)"
                    % (kind, ticket["id"], f["id"], ticket["id"], f["id"], ticket["id"], f["id"])
                )
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
                if current is not None and (kind == "implementer" or kind in LENS_KINDS):
                    attempt = current["attempts"] + (1 if kind == "implementer" else 0)
                    line = self.attempt_hint(task, {"kind": kind, "attempt": attempt, "phase": current["n"]})
                    hint = " (%s)" % line if line else ""
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
