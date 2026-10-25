"""The ticket machine end to end through its CLI: every acquire condition is a case, the
settlement rules, the commit gate, attempts, rulings, deferrals and the engram fallback."""

import json
import os
import tempfile
import unittest

from helpers import DESIGN_ES, SCOPE_REPORT, ProjectCase, finding, fragment, full_receipt, receipt_block


class NoProject(unittest.TestCase):
    def test_no_ai_team_dir_is_a_usage_error(self):
        from helpers import run
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            code, _, err = run("status", cwd=tmp)
            self.assertEqual(code, 2)
            self.assertIn("not an ai-team project", err)


class BoundedFlow(ProjectCase):
    def test_full_bounded_lifecycle(self):
        _, out, _ = self.ai("status")
        self.assertIn("no task in progress", out)
        self.assertIn("classify", out)
        self.ai("new", "demo", "--kind", "bounded")
        self.assertTrue(self.task()["task"].endswith("-demo"))
        # a second active task is refused
        self.ai("new", "other", "--kind", "bounded", expect=1)
        # no plan, no implementer
        _, _, err = self.ai("acquire", "implementer", expect=1)
        self.assertIn("no plan yet", err)
        self.ai("plan", "generate", "--objective", "Add a flag", "--decision", "off by default",
                "--check", "python3 -c 'import src.app'", "--failure", "ModuleNotFoundError when src/app.py is missing",
                "--file", "src/app.py", "--out-of-scope", "docs")
        plan = self.read(".ai-team/plans/%s.md" % self.task()["task"])
        self.assertIn("off by default", plan)
        self.assertIn('"kind": "plan"', plan)
        _, out, _ = self.ai("phase", "extract", "1")
        brief = self.read(out.strip())
        self.assertIn("## Constraints", brief)
        self.assertIn('"allowed_edit_roots": [\n    "src"', brief)
        self.ai("acquire", "implementer")
        self.assertEqual(self.task()["phases"][0]["attempts"], 1)
        self.ai("acquire", "implementer", expect=1)  # open ticket
        # figures are mandatory
        _, _, err = self.ai("settle", "t1", "--outcome", "ok", expect=2)
        self.assertIn("--model", err)
        self.ai("settle", "t1", "--outcome", "ok", "--model", "sonnet", "--tokens", "10", "--tool-uses", "2", "--duration", "5")
        # tier must be declared before commit-check passes
        self.ai("commit-check", "--phase", "1", expect=1)
        self.ai("tier", "0", "--phase", "1", "--reason", "docs only")
        self.ai("commit-check", "--phase", "1")
        self.ai("phase", "done", "1", "--commit", "not-a-commit", expect=1)
        self.ai("phase", "done", "1", "--commit", self.head)
        self.assertEqual(self.task()["phases"][0]["status"], "committed")
        _, out, err = self.ai("close")
        self.assertIn("done", out)
        self.assertIn("engram not available", err)  # PATH without engram: warning, exit 0
        self.assertEqual(self.task()["status"], "done")
        self.ai("acquire", "retro")
        self.assertEqual(self.task()["tickets"][-1]["kind"], "retro")

    def test_tier_needs_a_settled_implementer(self):
        self.ai("new", "demo", "--kind", "bounded")
        self.ai("plan", "generate", "--objective", "x", "--check", "true", "--failure", "never green when the shell is broken", "--file", "README.md")
        _, _, err = self.ai("tier", "1", "--phase", "1", "--reason", "code", expect=1)
        self.assertIn("settle the implementer", err)

    def test_pause_and_resume(self):
        self.ai("new", "demo", "--kind", "bounded")
        self.ai("pause", "--question", "which flag name?")
        _, out, _ = self.ai("status")
        self.assertIn("Paused:", out)
        self.assertIn("which flag name?", out)
        self.ai("new", "second", "--kind", "bounded")
        self.ai("resume", expect=1)  # another task is active
        self.ai("pause")
        self.ai("resume", expect=1)  # two paused: say which
        self.ai("resume", self.task()["task"])


class LargeFlow(ProjectCase):
    def _design(self, security="pending", body="- Rechazar valores fuera de la lista blanca."):
        return self.write(".ai-team/designs/2026-09-05-demo.md", DESIGN_ES.format(security=security, security_body=body))

    def _implement(self, phase, outcome="ok"):
        _, out, _ = self.ai("acquire", "implementer", "--phase", str(phase))
        ticket = out.split()[1]
        self.ai("settle", ticket, "--outcome", outcome, "--model", "sonnet", "--tokens", "100", "--tool-uses", "3", "--duration", "9")
        return ticket

    def _review(self, phase, receipt, expect=0, defer=None):
        _, out, _ = self.ai("acquire", "reviewer", "--phase", str(phase))
        ticket = out.split()[1]
        report = self.write(".ai-team/reviews/%s-%s.md" % (ticket, phase), receipt_block(receipt))
        args = ["settle", ticket, "--outcome", "ok", "--model", "sonnet", "--tokens", "50", "--tool-uses", "4", "--duration", "7", "--report", report]
        if defer:
            args += ["--defer", defer]
        code, out, err = self.ai(*args, expect=expect)
        return ticket, out, err

    def test_attach_gives_a_designless_large_task_its_threat_model(self):
        _, out, _ = self.ai("new", "2026-09-05-demo", "--kind", "large")
        self.assertIn("design attach", out)
        self.assertLess(out.index("design attach"), out.index("design approve"))
        _, _, err = self.ai("acquire", "security-threat-model", expect=1)
        self.assertIn("ai-team design attach <path>", err)
        design = self._design()
        _, out, _ = self.ai("design", "attach", design)
        self.assertIn("attached", out)
        self.assertEqual(self.task()["design"], design)
        _, out, _ = self.ai("status")
        self.assertIn("Design: draft, security pending", out)
        self.ai("acquire", "security-threat-model")
        self.assertEqual(self.task()["tickets"][-1]["kind"], "security-threat-model")

    def test_attach_refuses_what_is_not_a_draft_design(self):
        self.ai("new", "2026-09-05-demo", "--kind", "large")
        self.ai("design", "attach", ".ai-team/designs/missing.md", expect=2)
        with tempfile.TemporaryDirectory() as elsewhere:
            outside = os.path.join(elsewhere, "design.md")
            with open(outside, "w", encoding="utf-8") as handle:
                handle.write(DESIGN_ES.format(security="pending", security_body="- x"))
            self.ai("design", "attach", outside, expect=2)
        notes = self.write(".ai-team/designs/notes.md", "just some notes, no frontmatter\n")
        _, _, err = self.ai("design", "attach", notes, expect=2)
        self.assertIn("status", err)
        self.assertIsNone(self.task().get("design"))
        design = self._design()
        self.ai("design", "attach", design)
        other = self.write(".ai-team/designs/other.md", DESIGN_ES.format(security="pending", security_body="- x"))
        _, _, err = self.ai("design", "attach", other, expect=1)
        self.assertIn(design, err)
        self.ai("design", "attach", design)  # the same path again is a no-op
        self.assertEqual(self.task()["design"], design)

    def test_attach_is_for_a_large_task_in_progress(self):
        design = self._design()
        self.ai("design", "attach", design, expect=1)  # no task in progress
        self.ai("new", "demo", "--kind", "bounded")
        _, _, err = self.ai("design", "attach", design, expect=1)
        self.assertIn("large", err)

    def test_design_gates_then_scope_then_phases(self):
        design = self._design()
        self.ai("new", "2026-09-05-demo", "--kind", "large", "--design", design)
        _, out, _ = self.ai("status")
        self.assertIn("Design: draft, security pending", out)
        self.assertIn("Card: design", out)
        # the threat-model must run before approval
        self.ai("design", "approve", design, expect=1)
        self.ai("acquire", "scout-scope", expect=1)
        self.ai("acquire", "security-threat-model")
        # scout-map shares the floor only with other scout-map tickets; t1 is a threat-model
        self.ai("acquire", "scout-map", expect=1)
        self.assertEqual(self.task()["tickets"][-1]["kind"], "security-threat-model")
        self.ai("settle", "t1", "--outcome", "ok", "--model", "sonnet", "--tokens", "1", "--tool-uses", "1", "--duration", "1",
                "--report", self.write(".ai-team/reviews/tm.md", "# threat model\n"))
        self.assertIn("security: \"done\"", self.read(design))
        self.ai("design", "approve", design)
        self.assertEqual(self.task()["design"], design)
        # implementer still needs a plan and a scope decision
        _, _, err = self.ai("acquire", "implementer", "--phase", "1", expect=1)
        self.assertIn("scout-scope", err)
        self.ai("acquire", "scout-scope")
        self.ai("settle", "t2", "--outcome", "ok", "--model", "sonnet", "--tokens", "1", "--tool-uses", "1", "--duration", "1", expect=1)  # report required
        scope = self.write(".ai-team/explorations/2026-09-05-demo-scope.md", SCOPE_REPORT)
        self.ai("settle", "t2", "--outcome", "ok", "--model", "sonnet", "--tokens", "1", "--tool-uses", "1", "--duration", "1", "--report", scope)
        self.assertEqual(self.task()["scope_report"], scope)
        # a large task never takes --objective
        self.ai("plan", "generate", "--objective", "x", "--check", "true", expect=1)
        _, out, _ = self.ai("plan", "generate")
        self.assertIn("2 phases", out)
        plan = json.loads(self.read(self.task()["plan"]).split("```json\n")[1].split("\n```")[0])
        self.assertEqual(plan["phases"][0]["expected_files"][0]["path"], "src/flags.py")
        self.assertEqual(plan["phases"][0]["allowed_edit_roots"], ["src"])
        self.assertIn("security: Rechazar valores fuera de la lista blanca.", plan["constraints"])
        self.assertEqual(plan["phases"][0]["scout_notes"], ["src/app.py:1 -- VALUE is read at import time"])
        # phases go in order
        _, _, err = self.ai("acquire", "implementer", "--phase", "2", expect=1)
        self.assertIn("phase 1 is not committed", err)
        self._implement(1)
        self.ai("tier", "1", "--phase", "1", "--reason", "code")
        # a broken report keeps the ticket open
        _, out, _ = self.ai("acquire", "reviewer", "--phase", "1")
        reviewer = out.split()[1]
        bad = self.write(".ai-team/reviews/bad.md", "# no block here\n")
        _, _, err = self.ai("settle", reviewer, "--outcome", "ok", "--model", "sonnet", "--tokens", "1", "--tool-uses", "1", "--duration", "1", "--report", bad, expect=1)
        self.assertIn("no fenced", err)
        self.assertIsNone(self.task()["tickets"][-1]["settled_at"])
        # a fragment is not a reviewer receipt
        frag = self.write(".ai-team/reviews/frag.md", receipt_block(fragment()))
        self.ai("settle", reviewer, "--outcome", "ok", "--model", "sonnet", "--tokens", "1", "--tool-uses", "1", "--duration", "1", "--report", frag, expect=1)
        good = self.write(".ai-team/reviews/good.md", receipt_block(full_receipt([finding("F-1", "MINOR")])))
        self.ai("settle", reviewer, "--outcome", "ok", "--model", "sonnet", "--tokens", "1", "--tool-uses", "1", "--duration", "1", "--report", good, "--defer", "F-1")
        debt = self.read(".ai-team/tech-debt.md")
        self.assertIn("| MINOR |", debt)
        self.assertIn("F-1 claim", debt)
        self.ai("commit-check", "--phase", "1")
        self.ai("phase", "done", "1", "--commit", self.head)
        self.ai("debt", "fix", "--match", "F-1", "--commit", self.head[:10])
        self.assertIn("fixed (%s)" % self.head[:10], self.read(".ai-team/tech-debt.md"))
        self.ai("close", expect=1)  # phase 2 pending
        self._implement(2)
        self.ai("tier", "0", "--phase", "2", "--reason", "rename only")
        self.ai("acquire", "reviewer", "--phase", "2", expect=1)  # tier 0: no reviewer
        self.ai("phase", "done", "2", "--commit", self.head)
        self.ai("close")

    def test_blocked_review_attempts_rulings_and_trend(self):
        design = self._design(security="not-needed", body="No aplica: sin entrada externa.")
        self.ai("new", "2026-09-05-demo", "--kind", "large", "--design", design)
        self.ai("design", "approve", design)
        self.ai("plan", "generate", "--scope-skipped", "the map pass documented every file line by line")
        self.assertEqual(self.task()["scope_skipped"], "the map pass documented every file line by line")
        self._implement(1)
        self.ai("tier", "2", "--phase", "1", "--reason", "parses untrusted input")
        critical = finding("F-1", "CRITICAL", evidence="executed")
        _, out, _ = self._review(1, full_receipt([critical, finding("F-2")]))
        self.assertIn("review-blocked", out)
        # reviewer settled for this attempt: a second one is refused, the implementer may retry
        self.ai("acquire", "reviewer", "--phase", "1", expect=1)
        _, _, err = self.ai("commit-check", "--phase", "1", expect=1)
        self.assertIn("without a ruling", err + _)
        # attempt 2 resumes the same implementer; findings did not decrease -> warning
        _, out, _ = self.ai("acquire", "implementer", "--phase", "1")
        self.assertIn("attempt 2: resume", out)
        self.ai("settle", out.split()[1], "--outcome", "ok", "--model", "sonnet", "--tokens", "1", "--tool-uses", "1", "--duration", "1")
        self._review(1, full_receipt([critical, finding("F-2"), finding("F-3")]))
        _, out, _ = self.ai("status")
        self.assertIn("findings did not decrease", out)
        # security-audit at tier 2 runs after the reviewer settled; its CRITICAL also blocks
        _, out, _ = self.ai("acquire", "security-audit", "--phase", "1")
        sec = out.split()[1]
        sec_report = self.write(".ai-team/reviews/sec.md", receipt_block(fragment([finding("S-1", "CRITICAL", evidence="executed")])))
        self.ai("settle", sec, "--outcome", "ok", "--model", "sonnet", "--tokens", "1", "--tool-uses", "1", "--duration", "1", "--report", sec_report)
        self.assertEqual(self.task()["tickets"][-1]["verdict"], "review-blocked")
        code, out, _ = self.ai("commit-check", "--phase", "1", expect=1)
        self.assertIn("F-1", out)
        self.assertIn("S-1", out)
        # rulings clear the gate finding by finding
        reviewer_ticket = [t for t in self.task()["tickets"] if t["kind"] == "reviewer"][-1]["id"]
        self.ai("ruling", reviewer_ticket, "--finding", "F-9", "--text", "x", "--cost-if-wrong", "y", expect=1)
        self.ai("ruling", reviewer_ticket, "--finding", "F-1", "--text", "false positive: guarded at app.py:3", "--cost-if-wrong", "a crash on empty input")
        self.ai("commit-check", "--phase", "1", expect=1)
        self.ai("ruling", sec, "--finding", "S-1", "--text", "accepted by the user", "--cost-if-wrong", "data exposure")
        self.ai("commit-check", "--phase", "1")
        self.assertEqual(len(self.task()["rulings"]), 2)

    def _committed_tier_one_phase(self, receipt, defer=None):
        design = self._design(security="not-needed", body="No aplica.")
        self.ai("new", "2026-09-05-demo", "--kind", "large", "--design", design)
        self.ai("design", "approve", design)
        self.ai("plan", "generate", "--scope-skipped", "covered by the map")
        self._implement(1)
        self.ai("tier", "1", "--phase", "1", "--reason", "code")
        ticket, _, _ = self._review(1, receipt, defer=defer)
        self.ai("phase", "done", "1", "--commit", self.head)
        self._commit_tier_zero_phase(2)
        return ticket

    def _commit_tier_zero_phase(self, phase):
        self._implement(phase)
        self.ai("tier", "0", "--phase", str(phase), "--reason", "rename only")
        self.ai("phase", "done", str(phase), "--commit", self.head)

    def test_close_refuses_a_minor_finding_without_ruling_or_deferral(self):
        self._committed_tier_one_phase(full_receipt([finding("F-1", "MINOR")]))
        _, _, err = self.ai("close", expect=1)
        self.assertIn("F-1", err)
        self.assertIn("ai-team ruling", err)
        self.assertIn("--defer", err)
        self.assertIn("has already passed", err)  # a deferral belongs to the lens's settle, now settled
        self.assertNotIn("or `ai-team settle", err)  # the only verb offered now is the ruling
        self.assertEqual(self.task()["status"], "active")

    def test_close_reads_the_lens_kinds_from_the_settled_tickets_not_from_the_tier(self):
        self._committed_tier_one_phase(full_receipt([finding("F-1", "MINOR")]))
        task_file = os.path.join(self.root, ".ai-team", "tasks", sorted(os.listdir(os.path.join(self.root, ".ai-team", "tasks")))[-1])
        task = self.task()
        task["phases"][0]["tier"] = 0
        with open(task_file, "w") as handle:
            json.dump(task, handle)
        _, _, err = self.ai("close", expect=1)
        self.assertIn("F-1", err)

    def test_tier_of_a_committed_phase_cannot_be_lowered(self):
        self._committed_tier_one_phase(full_receipt([finding("F-1", "MINOR")]))
        _, _, err = self.ai("tier", "--phase", "1", "0", "--reason", "docs only", expect=1)
        self.assertIn("phase 1", err)
        self.assertIn("tier 1", err)
        self.assertEqual(self.task()["phases"][0]["tier"], 1)
        self.ai("tier", "--phase", "1", "2", "--reason", "more review is allowed")

    def test_close_accepts_a_minor_finding_that_was_deferred(self):
        self._committed_tier_one_phase(full_receipt([finding("F-1", "MINOR")]), defer="F-1")
        self.ai("close")
        self.assertEqual(self.task()["status"], "done")

    def test_close_accepts_a_minor_finding_that_was_ruled(self):
        ticket = self._committed_tier_one_phase(full_receipt([finding("F-1", "MINOR")]))
        self.ai("ruling", ticket, "--finding", "F-1", "--text", "accepted by the user", "--cost-if-wrong", "a cosmetic flaw")
        self.ai("close")
        self.assertEqual(self.task()["status"], "done")

    def test_close_checks_the_security_audit_receipt_of_a_tier_two_phase(self):
        design = self._design(security="not-needed", body="No aplica.")
        self.ai("new", "2026-09-05-demo", "--kind", "large", "--design", design)
        self.ai("design", "approve", design)
        self.ai("plan", "generate", "--scope-skipped", "covered by the map")
        self._implement(1)
        self.ai("tier", "2", "--phase", "1", "--reason", "parses untrusted input")
        self._review(1, full_receipt([]))
        _, out, _ = self.ai("acquire", "security-audit", "--phase", "1")
        sec = out.split()[1]
        sec_report = self.write(".ai-team/reviews/sec.md", receipt_block(fragment([finding("S-1", "MINOR")])))
        self.ai("settle", sec, "--outcome", "ok", "--model", "sonnet", "--tokens", "1", "--tool-uses", "1", "--duration", "1", "--report", sec_report)
        self.ai("phase", "done", "1", "--commit", self.head)
        self._commit_tier_zero_phase(2)
        _, _, err = self.ai("close", expect=1)
        self.assertIn("S-1", err)
        self.assertIn("security-audit", err)

    def test_major_finding_blocks_until_ruled_or_deferred(self):
        design = self._design(security="not-needed", body="No aplica.")
        self.ai("new", "2026-09-05-demo", "--kind", "large", "--design", design)
        self.ai("design", "approve", design)
        self.ai("plan", "generate", "--scope-skipped", "covered by the map")
        self._implement(1)
        self.ai("tier", "1", "--phase", "1", "--reason", "code")
        _, out, _ = self._review(1, full_receipt([finding("F-1", "MAJOR")]))
        self.assertNotIn("review-blocked", out)  # the receipt is review-clear -- the gate still fires
        _, out, _ = self.ai("commit-check", "--phase", "1", expect=1)
        self.assertIn("F-1", out)
        self.assertIn("MAJOR", out)
        self.assertIn("ruling", out)
        self.assertIn("--defer", out)
        reviewer_ticket = [t for t in self.task()["tickets"] if t["kind"] == "reviewer"][-1]["id"]
        self.ai("ruling", reviewer_ticket, "--finding", "F-1", "--text", "accepted", "--cost-if-wrong", "a regression")
        self.ai("commit-check", "--phase", "1")
        self.ai("phase", "done", "1", "--commit", self.head)
        # phase 2: the same shape, cleared by a deferral instead of a ruling
        self._implement(2)
        self.ai("tier", "1", "--phase", "2", "--reason", "code")
        self.ai("commit-check", "--phase", "2", expect=1)
        self._review(2, full_receipt([finding("F-1", "MAJOR")]), defer="F-1")
        self.ai("commit-check", "--phase", "2")

    def test_defer_refuses_critical_finding(self):
        design = self._design(security="not-needed", body="No aplica.")
        self.ai("new", "2026-09-05-demo", "--kind", "large", "--design", design)
        self.ai("design", "approve", design)
        self.ai("plan", "generate", "--scope-skipped", "covered by the map")
        self._implement(1)
        self.ai("tier", "1", "--phase", "1", "--reason", "code")
        _, out, _ = self.ai("acquire", "reviewer", "--phase", "1")
        ticket = out.split()[1]
        report = self.write(".ai-team/reviews/%s.md" % ticket,
                             receipt_block(full_receipt([finding("S-1", "CRITICAL", evidence="executed")])))
        debt_path = os.path.join(self.root, ".ai-team", "tech-debt.md")
        self.assertFalse(os.path.exists(debt_path))
        _, _, err = self.ai("settle", ticket, "--outcome", "ok", "--model", "sonnet", "--tokens", "1",
                             "--tool-uses", "1", "--duration", "1", "--report", report, "--defer", "S-1", expect=1)
        self.assertIn("ai-team ruling", err)
        self.assertFalse(os.path.exists(debt_path))  # a refused settle writes nothing
        # the ticket stayed open: settle it for real, a CRITICAL is cleared by a ruling only
        self.ai("settle", ticket, "--outcome", "ok", "--model", "sonnet", "--tokens", "1", "--tool-uses", "1",
                "--duration", "1", "--report", report)
        self.ai("commit-check", "--phase", "1", expect=1)
        self.ai("ruling", ticket, "--finding", "S-1", "--text", "accepted", "--cost-if-wrong", "data exposure")
        self.ai("commit-check", "--phase", "1")

    def test_disposition_matches_by_id_file_and_severity(self):
        design = self._design(security="not-needed", body="No aplica.")
        self.ai("new", "2026-09-05-demo", "--kind", "large", "--design", design)
        self.ai("design", "approve", design)
        self.ai("plan", "generate", "--scope-skipped", "covered by the map")
        self._implement(1)
        self.ai("tier", "1", "--phase", "1", "--reason", "code")
        self._review(1, full_receipt([finding("F-1", "MAJOR", file="src/app.py")]), defer="F-1")
        self.ai("commit-check", "--phase", "1")
        # attempt 2: same id, same file, same severity -- the attempt-1 deferral still satisfies it
        self._implement(1)
        self._review(1, full_receipt([finding("F-1", "MAJOR", file="src/app.py")]))
        self.ai("commit-check", "--phase", "1")
        # attempt 3: the severity increases to CRITICAL -- a new, undispositioned finding
        self._implement(1)
        self._review(1, full_receipt([finding("F-1", "CRITICAL", file="src/app.py", evidence="executed")]))
        _, out, _ = self.ai("commit-check", "--phase", "1", expect=1)
        self.assertIn("F-1", out)
        reviewer3 = [t for t in self.task()["tickets"] if t["kind"] == "reviewer"][-1]["id"]
        self.ai("ruling", reviewer3, "--finding", "F-1", "--text", "accepted", "--cost-if-wrong", "a crash")
        self.ai("commit-check", "--phase", "1")
        # attempt 4: back to MAJOR, but at a different file -- a new, undispositioned finding
        self.write("src/b.py", "OTHER = 1\n")
        self._implement(1)
        self._review(1, full_receipt([finding("F-1", "MAJOR", file="src/b.py")]))
        _, out, _ = self.ai("commit-check", "--phase", "1", expect=1)
        self.assertIn("F-1", out)

    def test_delta_receipt_must_account_for_every_prior_major_critical(self):
        design = self._design(security="not-needed", body="No aplica.")
        self.ai("new", "2026-09-05-demo", "--kind", "large", "--design", design)
        self.ai("design", "approve", design)
        self.ai("plan", "generate", "--scope-skipped", "covered by the map")
        self._implement(1)
        self.ai("tier", "1", "--phase", "1", "--reason", "code")
        self._review(1, full_receipt([finding("F-1", "MAJOR"), finding("F-2", "MAJOR")]))
        self._implement(1)  # attempt 2
        _, out, _ = self.ai("acquire", "reviewer", "--phase", "1")
        ticket = out.split()[1]
        report_path = ".ai-team/reviews/%s.md" % ticket
        empty = self.write(report_path, receipt_block(full_receipt([])))
        _, _, err = self.ai("settle", ticket, "--outcome", "ok", "--model", "sonnet", "--tokens", "1",
                             "--tool-uses", "1", "--duration", "1", "--report", empty, expect=1)
        self.assertIn("F-1", err)
        self.assertIn("F-2", err)
        self.assertIsNone(self.ticket_by_id(ticket)["settled_at"])
        # re-listing F-2 and closing F-1 with a citation accounts for both
        good = self.write(report_path, receipt_block(
            full_receipt([finding("F-2", "MAJOR")], closed=[{"id": "F-1", "file": "src/app.py", "line": 1}])))
        self.ai("settle", ticket, "--outcome", "ok", "--model", "sonnet", "--tokens", "1", "--tool-uses", "1",
                "--duration", "1", "--report", good)
        _, out, _ = self.ai("commit-check", "--phase", "1", expect=1)
        self.assertIn("F-2", out)
        self.assertNotIn("F-1", out)

    def test_closed_on_a_fresh_attempt_is_refused(self):
        design = self._design(security="not-needed", body="No aplica.")
        self.ai("new", "2026-09-05-demo", "--kind", "large", "--design", design)
        self.ai("design", "approve", design)
        self.ai("plan", "generate", "--scope-skipped", "covered by the map")
        self._implement(1)
        self.ai("tier", "1", "--phase", "1", "--reason", "code")
        _, out, _ = self.ai("acquire", "reviewer", "--phase", "1")
        ticket = out.split()[1]
        report = self.write(".ai-team/reviews/%s.md" % ticket, receipt_block(
            full_receipt([], closed=[{"id": "F-1", "file": "src/app.py", "line": 1}])))
        _, _, err = self.ai("settle", ticket, "--outcome", "ok", "--model", "sonnet", "--tokens", "1",
                             "--tool-uses", "1", "--duration", "1", "--report", report, expect=1)
        self.assertIn("attempt", err)
        self.assertIsNone(self.ticket_by_id(ticket)["settled_at"])

    def test_deferred_prior_finding_may_be_omitted_from_the_delta_receipt(self):
        design = self._design(security="not-needed", body="No aplica.")
        self.ai("new", "2026-09-05-demo", "--kind", "large", "--design", design)
        self.ai("design", "approve", design)
        self.ai("plan", "generate", "--scope-skipped", "covered by the map")
        self._implement(1)
        self.ai("tier", "1", "--phase", "1", "--reason", "code")
        self._review(1, full_receipt([finding("F-1", "MAJOR")]), defer="F-1")
        self._implement(1)
        _, out, _ = self.ai("acquire", "reviewer", "--phase", "1")
        ticket = out.split()[1]
        report = self.write(".ai-team/reviews/%s.md" % ticket, receipt_block(full_receipt([])))
        self.ai("settle", ticket, "--outcome", "ok", "--model", "sonnet", "--tokens", "1", "--tool-uses", "1",
                "--duration", "1", "--report", report)
        self.ai("commit-check", "--phase", "1")

    def test_reconciliation_skips_a_reportless_prior_and_reaches_further_back(self):
        design = self._design(security="not-needed", body="No aplica.")
        self.ai("new", "2026-09-05-demo", "--kind", "large", "--design", design)
        self.ai("design", "approve", design)
        self.ai("plan", "generate", "--scope-skipped", "covered by the map")
        self._implement(1)
        self.ai("tier", "1", "--phase", "1", "--reason", "code")
        self._review(1, full_receipt([finding("F-1", "MAJOR")]))
        reviewer1 = [t for t in self.task()["tickets"] if t["kind"] == "reviewer"][-1]["id"]
        self._implement(1)  # attempt 2
        _, out, _ = self.ai("acquire", "reviewer", "--phase", "1")
        ticket2 = out.split()[1]
        self.ai("settle", ticket2, "--outcome", "blocked", "--model", "sonnet", "--tokens", "1",
                "--tool-uses", "1", "--duration", "1")  # blocked, no --report -- reconciliation skips it
        self._implement(1)  # attempt 3
        _, out, _ = self.ai("acquire", "reviewer", "--phase", "1")
        ticket3 = out.split()[1]
        report = self.write(".ai-team/reviews/%s.md" % ticket3, receipt_block(full_receipt([])))
        _, _, err = self.ai("settle", ticket3, "--outcome", "ok", "--model", "sonnet", "--tokens", "1",
                             "--tool-uses", "1", "--duration", "1", "--report", report, expect=1)
        self.assertIn("F-1", err)
        self.assertIn(reviewer1, err)

    def test_reconciliation_refusal_writes_nothing_to_tech_debt(self):
        design = self._design(security="not-needed", body="No aplica.")
        self.ai("new", "2026-09-05-demo", "--kind", "large", "--design", design)
        self.ai("design", "approve", design)
        self.ai("plan", "generate", "--scope-skipped", "covered by the map")
        self._implement(1)
        self.ai("tier", "1", "--phase", "1", "--reason", "code")
        self._review(1, full_receipt([finding("F-1", "MAJOR"), finding("F-2", "MINOR")]), defer="F-2")
        before = self.read(".ai-team/tech-debt.md")
        self._implement(1)
        _, out, _ = self.ai("acquire", "reviewer", "--phase", "1")
        ticket = out.split()[1]
        bad = self.write(".ai-team/reviews/%s.md" % ticket, receipt_block(full_receipt([])))
        self.ai("settle", ticket, "--outcome", "ok", "--model", "sonnet", "--tokens", "1", "--tool-uses", "1",
                "--duration", "1", "--report", bad, expect=1)
        self.assertEqual(self.read(".ai-team/tech-debt.md"), before)

    def test_reconciliation_refusal_fires_before_defer_in_the_same_settle_call(self):
        # F-2 is a legitimate --defer target THIS pass (re-listed); F-1 is silently dropped.
        # If reconciliation ever ran after --defer's debt.append_findings, F-2 would land in
        # tech-debt.md before the F-1 refusal was even raised.
        design = self._design(security="not-needed", body="No aplica.")
        self.ai("new", "2026-09-05-demo", "--kind", "large", "--design", design)
        self.ai("design", "approve", design)
        self.ai("plan", "generate", "--scope-skipped", "covered by the map")
        self._implement(1)
        self.ai("tier", "1", "--phase", "1", "--reason", "code")
        self._review(1, full_receipt([finding("F-1", "MAJOR"), finding("F-2", "MAJOR"), finding("F-3", "MINOR")]), defer="F-3")
        before = self.read(".ai-team/tech-debt.md")
        self._implement(1)
        _, out, _ = self.ai("acquire", "reviewer", "--phase", "1")
        ticket = out.split()[1]
        report = self.write(".ai-team/reviews/%s.md" % ticket, receipt_block(full_receipt([finding("F-2", "MAJOR")])))
        _, _, err = self.ai("settle", ticket, "--outcome", "ok", "--model", "sonnet", "--tokens", "1",
                             "--tool-uses", "1", "--duration", "1", "--report", report, "--defer", "F-2", expect=1)
        self.assertIn("F-1", err)
        self.assertEqual(self.read(".ai-team/tech-debt.md"), before)
        self.assertIsNone(self.ticket_by_id(ticket)["settled_at"])
        self.assertEqual(self.ticket_by_id(ticket)["deferred"], [])

    def test_closed_naming_an_id_the_prior_receipt_never_reported_is_refused(self):
        design = self._design(security="not-needed", body="No aplica.")
        self.ai("new", "2026-09-05-demo", "--kind", "large", "--design", design)
        self.ai("design", "approve", design)
        self.ai("plan", "generate", "--scope-skipped", "covered by the map")
        self._implement(1)
        self.ai("tier", "1", "--phase", "1", "--reason", "code")
        self._review(1, full_receipt([finding("F-1", "MAJOR")]))
        self._implement(1)
        _, out, _ = self.ai("acquire", "reviewer", "--phase", "1")
        ticket = out.split()[1]
        report = self.write(".ai-team/reviews/%s.md" % ticket, receipt_block(
            full_receipt([], closed=[{"id": "F-9", "file": "src/app.py", "line": 1}])))
        _, _, err = self.ai("settle", ticket, "--outcome", "ok", "--model", "sonnet", "--tokens", "1",
                             "--tool-uses", "1", "--duration", "1", "--report", report, expect=1)
        self.assertIn("F-9", err)
        self.assertIsNone(self.ticket_by_id(ticket)["settled_at"])

    def test_no_prior_report_prints_a_note_and_still_refuses_a_nonempty_closed(self):
        design = self._design(security="not-needed", body="No aplica.")
        self.ai("new", "2026-09-05-demo", "--kind", "large", "--design", design)
        self.ai("design", "approve", design)
        self.ai("plan", "generate", "--scope-skipped", "covered by the map")
        self._implement(1)
        self.ai("tier", "1", "--phase", "1", "--reason", "code")
        _, out, _ = self.ai("acquire", "reviewer", "--phase", "1")
        ticket1 = out.split()[1]
        # attempt 1's reviewer settles blocked with no report -- reconciliation for attempt 2
        # finds no earlier report-carrying ticket at all.
        self.ai("settle", ticket1, "--outcome", "blocked", "--model", "sonnet", "--tokens", "1",
                "--tool-uses", "1", "--duration", "1")
        self._implement(1)
        _, out, _ = self.ai("acquire", "reviewer", "--phase", "1")
        ticket2 = out.split()[1]
        report = self.write(".ai-team/reviews/%s.md" % ticket2, receipt_block(
            full_receipt([], closed=[{"id": "F-1", "file": "src/app.py", "line": 1}])))
        _, _, err = self.ai("settle", ticket2, "--outcome", "ok", "--model", "sonnet", "--tokens", "1",
                             "--tool-uses", "1", "--duration", "1", "--report", report, expect=1)
        self.assertIn("no earlier", err)
        self.assertIsNone(self.ticket_by_id(ticket2)["settled_at"])
        # the same shape with an empty closed settles, and the note names the phase
        empty = self.write(".ai-team/reviews/%s.md" % ticket2, receipt_block(full_receipt([])))
        _, out, _ = self.ai("settle", ticket2, "--outcome", "ok", "--model", "sonnet", "--tokens", "1",
                             "--tool-uses", "1", "--duration", "1", "--report", empty)
        self.assertIn("no earlier settled reviewer report for phase 1", out)

    def test_commit_check_refuses_on_report_drift(self):
        design = self._design(security="not-needed", body="No aplica.")
        self.ai("new", "2026-09-05-demo", "--kind", "large", "--design", design)
        self.ai("design", "approve", design)
        self.ai("plan", "generate", "--scope-skipped", "covered by the map")
        self._implement(1)
        self.ai("tier", "1", "--phase", "1", "--reason", "code")
        ticket, _, _ = self._review(1, full_receipt([finding("F-1", "MINOR")]))
        self.ai("commit-check", "--phase", "1")  # a MINOR-only receipt never blocks
        report_path = self.task()["tickets"][-1]["report"]
        tampered = full_receipt([finding("F-1", "MINOR")])
        tampered["lenses"]["correctness"]["findings"][0]["line"] = 99
        self.write(report_path, receipt_block(tampered))
        _, out, _ = self.ai("commit-check", "--phase", "1", expect=1)
        self.assertIn(ticket, out)
        self.assertIn(report_path, out)

    def test_attempts_cap_and_infra_death(self):
        design = self._design(security="not-needed", body="No aplica.")
        self.ai("new", "2026-09-05-demo", "--kind", "large", "--design", design)
        self.ai("design", "approve", design)
        self.ai("plan", "generate", "--scope-skipped", "covered by the map")
        self.ai("acquire", "implementer", "--phase", "1")
        self.ai("settle", "t1", "--outcome", "infra-death")
        self.assertEqual(self.task()["phases"][0]["attempts"], 0)
        for attempt in range(1, 7):
            self._implement(1, outcome="blocked")
            self.assertEqual(self.task()["phases"][0]["attempts"], attempt)
        _, _, err = self.ai("acquire", "implementer", "--phase", "1", expect=1)
        self.assertIn("reopen the design", err)
        # a blocked implementer widens the phase with a recorded reason
        self.ai("plan", "amend", "--phase", "1", "--reason", "needs src/util.py", "--file", "src/util.py")
        plan = self.read(self.task()["plan"])
        self.assertIn("needs src/util.py", plan)
        self.assertEqual(self.task()["phases"][0]["amendments"][0]["reason"], "needs src/util.py")

    def _planned_large_task(self):
        design = self._design(security="not-needed", body="No aplica.")
        self.ai("new", "2026-09-05-demo", "--kind", "large", "--design", design)
        self.ai("design", "approve", design)
        self.ai("plan", "generate", "--scope-skipped", "covered by the map")
        return design

    def test_design_amend_records_a_decision_in_design_plan_and_task(self):
        design = self._planned_large_task()
        decision = "Un flag vacío cuenta como apagado."
        _, out, _ = self.ai("design", "amend", "--phase", "1", "--reason", "review F-2 needs a rule for empty flags",
                            "--decision", decision, "--decision", "El flag se lee una sola vez.")
        self.assertIn("phase 1", out)
        text = self.read(design)
        decisions_section = text.split("## Decisiones")[1].split("## Diseño")[0]
        self.assertIn("- " + decision, decisions_section)
        self.assertIn("- El flag se lee una sola vez.", decisions_section)
        self.assertIn("- Un valor de flag no reconocido se rechaza, nunca se interpreta.", decisions_section)
        self.ai("phase", "extract", "1")
        phase_file = self.read(os.path.join(".ai-team", "plans", "2026-09-05-demo", "phase-1.md"))
        constraints = phase_file.split("## Constraints")[1].split("## Scenarios")[0]
        self.assertIn("- " + decision, constraints)
        amendment = self.task()["phases"][0]["amendments"][-1]
        self.assertEqual(amendment["decisions"], [decision, "El flag se lee una sola vez."])
        self.assertEqual(amendment["reason"], "review F-2 needs a rule for empty flags")
        self.assertEqual(self.task()["design"], design)

    def test_design_amend_keeps_the_design_approved(self):
        design = self._planned_large_task()
        self.ai("design", "amend", "--phase", "1", "--reason", "new rule", "--decision", "Regla nueva.")
        _, out, _ = self.ai("status")
        self.assertIn("Design: approved", out)
        self.assertIn('status: "approved"', self.read(design))

    def test_design_amend_names_the_verb_that_supplies_what_is_missing(self):
        self.ai("new", "2026-09-05-demo", "--kind", "large")
        _, _, err = self.ai("design", "amend", "--phase", "1", "--reason", "r", "--decision", "d", expect=1)
        self.assertIn("design attach", err)
        self.ai("design", "attach", self._design(security="not-needed", body="No aplica."))
        _, _, err = self.ai("design", "amend", "--phase", "1", "--reason", "r", "--decision", "d", expect=1)
        self.assertIn("plan generate", err)

    def test_design_amend_refuses_a_decision_the_plan_already_holds(self):
        design = self._planned_large_task()
        before = self.read(design)
        existing = "Un valor de flag no reconocido se rechaza, nunca se interpreta."
        _, _, err = self.ai("design", "amend", "--phase", "1", "--reason", "r", "--decision", "Regla nueva.",
                            "--decision", existing, expect=1)
        self.assertIn(existing, err)
        self.assertEqual(self.read(design), before)
        self.assertEqual(self.task()["phases"][0]["amendments"], [])
        self.ai("design", "amend", "--phase", "1", "--reason", "r", "--decision", "Regla nueva.")
        _, _, err = self.ai("design", "amend", "--phase", "1", "--reason", "again", "--decision", "Regla nueva.", expect=1)
        self.assertIn("Regla nueva.", err)

    def test_design_amend_refuses_the_same_decision_twice_in_one_call(self):
        design = self._planned_large_task()
        before = self.read(design)
        plan_before = self.read(self.task()["plan"])
        _, _, err = self.ai("design", "amend", "--phase", "1", "--reason", "r",
                            "--decision", "Regla nueva.", "--decision", "Regla nueva.", expect=1)
        self.assertIn("Regla nueva.", err)
        self.assertEqual(self.read(design), before)
        self.assertEqual(self.read(self.task()["plan"]), plan_before)
        self.assertEqual(self.task()["phases"][0]["amendments"], [])

    def test_design_amend_refuses_a_decision_that_is_not_one_line(self):
        design = self._planned_large_task()
        before = self.read(design)
        for bad in ("", "   ", "first line\nsecond line"):
            _, _, err = self.ai("design", "amend", "--phase", "1", "--reason", "r", "--decision", bad, expect=1)
            self.assertIn("one non-empty line", err)
            self.assertIn("--decision", err)
        self.assertEqual(self.read(design), before)
        self.assertEqual(self.task()["phases"][0]["amendments"], [])

    def test_design_amend_refuses_an_unknown_phase_without_touching_the_design(self):
        design = self._planned_large_task()
        before = self.read(design)
        _, _, err = self.ai("design", "amend", "--phase", "9", "--reason", "r", "--decision", "Regla nueva.", expect=1)
        self.assertIn("phase 9", err)
        self.assertEqual(self.read(design), before)

    def test_plan_regeneration_keeps_progress(self):
        design = self._design(security="not-needed", body="No aplica.")
        self.ai("new", "2026-09-05-demo", "--kind", "large", "--design", design)
        self.ai("design", "approve", design)
        self.ai("plan", "generate", "--scope-skipped", "covered")
        self._implement(1)
        self.ai("plan", "generate")
        self.assertEqual(self.task()["phases"][0]["attempts"], 1)


class Hooks(ProjectCase):
    def _payload(self, subagent, tool="Agent", cwd=None):
        return json.dumps({"session_id": "s", "cwd": cwd or self.root, "hook_event_name": "PreToolUse", "tool_name": tool,
                           "tool_input": {"description": "d", "prompt": "p", "subagent_type": subagent}})

    def _decision(self, out):
        return json.loads(out)["hookSpecificOutput"] if out.strip() else None

    def test_non_organic_and_non_agent_are_silent(self):
        for payload in (self._payload("Explore"), self._payload("organic-implementer", tool="Bash"), "not json", ""):
            code, out, _ = self.ai("hook", "pre-tool-use", stdin=payload)
            self.assertEqual(out, "")

    def test_outside_a_project_is_silent(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            _, out, _ = self.ai("hook", "pre-tool-use", stdin=self._payload("organic-implementer", cwd=tmp))
            self.assertEqual(out, "")
            _, out, _ = self.ai("hook", "session-start", stdin=json.dumps({"cwd": tmp, "hook_event_name": "SessionStart"}))
            self.assertEqual(out, "")

    def test_denies_without_task_then_without_ticket_then_allows(self):
        _, out, _ = self.ai("hook", "pre-tool-use", stdin=self._payload("organic-implementer"))
        decision = self._decision(out)
        self.assertEqual(decision["permissionDecision"], "deny")
        self.assertIn("ai-team new", decision["permissionDecisionReason"])
        self.ai("new", "demo", "--kind", "bounded")
        self.ai("plan", "generate", "--objective", "x", "--check", "true", "--failure", "never green when the shell is broken", "--file", "src/app.py")
        _, out, _ = self.ai("hook", "pre-tool-use", stdin=self._payload("organic-implementer"))
        self.assertIn("ai-team acquire implementer --phase 1", self._decision(out)["permissionDecisionReason"])
        self.ai("acquire", "implementer")
        _, out, _ = self.ai("hook", "pre-tool-use", stdin=self._payload("organic-implementer"))
        self.assertEqual(out, "")
        # a reviewer launch is still denied while only an implementer ticket is open
        _, out, _ = self.ai("hook", "pre-tool-use", stdin=self._payload("organic-reviewer"))
        self.assertEqual(self._decision(out)["permissionDecision"], "deny")
        # nested cwd walks up to the project
        sub = os.path.join(self.root, "src")
        _, out, _ = self.ai("hook", "pre-tool-use", stdin=self._payload("organic-implementer", cwd=sub))
        self.assertEqual(out, "")

    def test_session_start_prints_status(self):
        _, out, _ = self.ai("hook", "session-start", stdin=json.dumps({"cwd": self.root, "hook_event_name": "SessionStart", "source": "startup"}))
        self.assertIn("no task in progress", out)
        self.ai("new", "demo", "--kind", "bounded")
        _, out, _ = self.ai("hook", "session-start", stdin=json.dumps({"cwd": self.root}))
        self.assertIn("Task: ", out)
        self.assertIn("Allowed now", out)

    def test_retro_hook_uses_the_closed_task(self):
        self.ai("new", "demo", "--kind", "bounded")
        self.ai("plan", "generate", "--objective", "x", "--check", "true", "--failure", "never green when the shell is broken", "--file", "README.md")
        self.ai("acquire", "implementer")
        self.ai("settle", "t1", "--outcome", "ok", "--model", "sonnet", "--tokens", "1", "--tool-uses", "1", "--duration", "1")
        self.ai("tier", "0", "--phase", "1", "--reason", "docs")
        self.ai("phase", "done", "1", "--commit", self.head)
        self.ai("close")
        _, out, _ = self.ai("hook", "pre-tool-use", stdin=self._payload("organic-retro"))
        self.assertEqual(self._decision(out)["permissionDecision"], "deny")
        self.ai("acquire", "retro")
        _, out, _ = self.ai("hook", "pre-tool-use", stdin=self._payload("organic-retro"))
        self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main()
