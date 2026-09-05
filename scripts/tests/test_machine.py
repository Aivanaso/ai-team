"""The ticket machine end to end through its CLI: every acquire condition is a case, the
settlement rules, the commit gate, attempts, rulings, deferrals and the engram fallback."""

import json
import os
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
                "--check", "python3 -c 'import src.app'", "--file", "src/app.py", "--out-of-scope", "docs")
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
        self.ai("plan", "generate", "--objective", "x", "--check", "true", "--file", "README.md")
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
        # security-audit at tier 2 may run alongside; its CRITICAL also blocks
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
        self.ai("plan", "generate", "--objective", "x", "--check", "true", "--file", "src/app.py")
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
        self.ai("plan", "generate", "--objective", "x", "--check", "true", "--file", "README.md")
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
