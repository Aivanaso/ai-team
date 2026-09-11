"""Calibrated acceptance checks: a check enters a plan only with its calibration on paper.

Known negatives first (a gate is proven able to fail before its green counts): the scout's
report without calibration, a green with no failure signature, a red with no reason, a
zero-work digest, an `expect` that is not `exit N`. Then the machine running the checks the
orchestrator declares by CLI, the demotion of un-run checks to open questions, the
implementer gate on a phase with nothing calibrated, and legacy plans still rendering.
"""

import json
import unittest

from helpers import DESIGN_ES, ProjectCase


def scope_report(phase1_checks, phase2_checks=None, phase1_questions=(), phase1_omit_checks=False):
    phase1 = {"n": 1, "expected_files": [{"action": "CREATE", "path": "src/flags.py", "evidence": "src/app.py:1"}],
              "constraints_candidates": [], "open_questions": list(phase1_questions)}
    if not phase1_omit_checks:
        phase1["acceptance_checks"] = phase1_checks
    phase2 = {"n": 2, "expected_files": [{"action": "MODIFY", "path": "src/app.py", "evidence": "src/app.py:1"}],
              "acceptance_checks": phase2_checks if phase2_checks is not None else [GREEN_CHECK],
              "constraints_candidates": [], "open_questions": []}
    return "# Scope report\n\nprose\n\n```json\n%s\n```\n" % json.dumps({"kind": "scope-report", "phases": [phase1, phase2]})


GREEN_CHECK = {"command": "python3 -c 'import src.app'", "expect": "exit 0",
               "calibration": {"executed": True, "exit_code": 0, "digest": "(no output)",
                               "failure_signature": "ModuleNotFoundError when src/app.py is missing"}}
RED_CHECK = {"command": "python3 -c 'import src.flags'", "expect": "exit 0",
             "calibration": {"executed": True, "exit_code": 1, "digest": "ModuleNotFoundError: No module named 'src.flags'",
                             "red_reason": "src/flags.py is this phase's CREATE file"}}
UNRUN_CHECK = {"command": "composer tests",
               "calibration": {"executed": False, "target": "composer.json:140", "reason": "full suite is out of the read-only budget"}}


class ScopeCase(ProjectCase):
    """A large task with an approved design and an open scout-scope ticket (t1)."""

    def setUp(self):
        super().setUp()
        self.design = self.write(".ai-team/designs/2026-09-05-demo.md", DESIGN_ES.format(security="not-needed", security_body="No aplica."))
        self.ai("new", "2026-09-05-demo", "--kind", "large", "--design", self.design)
        self.ai("design", "approve", self.design)
        self.ai("acquire", "scout-scope")

    def settle_scope(self, report_text, expect=0):
        report = self.write(".ai-team/explorations/2026-09-05-demo-scope.md", report_text)
        return self.ai("settle", "t1", "--outcome", "ok", "--model", "sonnet", "--tokens", "1", "--tool-uses", "1", "--duration", "1",
                       "--report", report, expect=expect)

    def plan(self):
        return json.loads(self.read(self.task()["plan"]).split("```json\n")[1].split("\n```")[0])


class ScoutReportGate(ScopeCase):
    def test_free_text_verified_is_refused_and_the_ticket_stays_open(self):
        legacy = {"command": "python3 -c 'import src.app'", "verified": "not re-run in full this pass", "expect": "exit 0"}
        _, _, err = self.settle_scope(scope_report([legacy]), expect=1)
        self.assertIn("calibration", err)
        self.assertIn("relaunch the scout", err)
        self.assertIsNone(self.task()["tickets"][0]["settled_at"])

    def test_green_check_needs_a_failure_signature(self):
        check = json.loads(json.dumps(GREEN_CHECK))
        del check["calibration"]["failure_signature"]
        _, _, err = self.settle_scope(scope_report([check]), expect=1)
        self.assertIn("failure_signature", err)

    def test_red_check_needs_a_reason(self):
        check = json.loads(json.dumps(RED_CHECK))
        del check["calibration"]["red_reason"]
        _, _, err = self.settle_scope(scope_report([check]), expect=1)
        self.assertIn("red_reason", err)

    def test_zero_work_digest_is_never_a_green(self):
        for digest in ("No tests found", "No tests executed!", "No files analyzed", "Tests:       0 total", "0 files analyzed"):
            check = json.loads(json.dumps(GREEN_CHECK))
            check["calibration"]["digest"] = digest
            _, _, err = self.settle_scope(scope_report([check]), expect=1)
            self.assertIn("zero-work", err, digest)

    def test_expect_is_exit_n_or_nothing(self):
        check = json.loads(json.dumps(GREEN_CHECK))
        check["expect"] = "passes"
        _, _, err = self.settle_scope(scope_report([check]), expect=1)
        self.assertIn("exit N", err)

    def test_unrun_check_carries_no_expectation(self):
        check = json.loads(json.dumps(UNRUN_CHECK))
        check["expect"] = "exit 0"
        _, _, err = self.settle_scope(scope_report([check]), expect=1)
        self.assertIn("executed: false", err)
        self.assertIn("expect", err)

    def test_unrun_check_needs_target_and_reason(self):
        check = {"command": "composer tests", "calibration": {"executed": False}}
        _, _, err = self.settle_scope(scope_report([check]), expect=1)
        self.assertIn("target", err)
        self.assertIn("reason", err)

    def test_every_violation_is_reported_at_once(self):
        green = json.loads(json.dumps(GREEN_CHECK))
        del green["calibration"]["failure_signature"]
        red = json.loads(json.dumps(RED_CHECK))
        del red["calibration"]["red_reason"]
        _, _, err = self.settle_scope(scope_report([green, red]), expect=1)
        self.assertIn("failure_signature", err)
        self.assertIn("red_reason", err)


class ScopeIntoPlan(ScopeCase):
    def test_unrun_check_becomes_an_open_question_not_an_acceptance_check(self):
        self.settle_scope(scope_report([RED_CHECK, UNRUN_CHECK]))
        _, out, _ = self.ai("plan", "generate")
        phase = self.plan()["phases"][0]
        self.assertEqual([c["command"] for c in phase["acceptance_checks"]], ["python3 -c 'import src.flags'"])
        self.assertTrue(any("composer tests" in q and "not calibrated" in q for q in phase["open_questions"]), phase["open_questions"])
        self.assertIn("composer tests", out)
        self.assertIn("not calibrated", out)

    def test_red_today_is_printed_at_generate(self):
        self.settle_scope(scope_report([RED_CHECK]))
        _, out, _ = self.ai("plan", "generate")
        self.assertIn("red today", out)
        self.assertIn("src/flags.py is this phase's CREATE file", out)

    def test_calibration_travels_to_the_phase_file(self):
        self.settle_scope(scope_report([RED_CHECK]))
        self.ai("plan", "generate")
        _, out, _ = self.ai("phase", "extract", "1")
        phase_file = self.read(out.strip())
        self.assertIn("red today", phase_file)
        self.assertIn("ModuleNotFoundError", phase_file)
        block = json.loads(phase_file.split("```json\n")[1].split("\n```")[0])
        self.assertEqual(block["acceptance_checks"][0]["calibration"]["exit_code"], 1)

    def test_design_checks_neither_calibrated_nor_questioned_refuse_the_plan(self):
        self.settle_scope(scope_report([], phase1_omit_checks=True))
        _, _, err = self.ai("plan", "generate", expect=1)
        self.assertIn("phase 1", err)
        self.assertIn("neither calibrated nor questioned", err)

    def test_design_checks_questioned_is_enough(self):
        self.settle_scope(scope_report([], phase1_omit_checks=True, phase1_questions=["the design's check needs a fixture that does not exist yet"]))
        self.ai("plan", "generate")

    def test_phase_with_nothing_calibrated_blocks_the_implementer(self):
        self.settle_scope(scope_report([UNRUN_CHECK]))
        self.ai("plan", "generate")
        _, _, err = self.ai("acquire", "implementer", "--phase", "1", expect=1)
        self.assertIn("no calibrated acceptance check", err)
        self.assertIn("composer tests", err)
        self.assertIn("plan amend", err)
        # the loop closes: the orchestrator runs it through the machine
        self.ai("plan", "amend", "--phase", "1", "--reason", "ran the suite myself",
                "--check", "python3 -c 'import src.app'", "--failure", "ModuleNotFoundError when src/app.py is missing")
        self.ai("acquire", "implementer", "--phase", "1")


class MachineRunsCliChecks(ProjectCase):
    def bounded(self, *extra, expect=0):
        self.ai("new", "demo", "--kind", "bounded")
        return self.ai("plan", "generate", "--objective", "x", "--file", "src/app.py", *extra, expect=expect)

    def plan(self):
        return json.loads(self.read(self.task()["plan"]).split("```json\n")[1].split("\n```")[0])

    def test_check_needs_its_failure_flag(self):
        _, _, err = self.bounded("--check", "true", expect=2)
        self.assertIn("--failure", err)

    def test_check_and_failure_counts_match(self):
        _, _, err = self.bounded("--check", "true", "--check", "true", "--failure", "one", expect=2)
        self.assertIn("--failure", err)

    def test_green_check_is_run_and_recorded(self):
        self.bounded("--check", "python3 -c 'import src.app; print(\"VALUE\", src.app.VALUE)'", "--failure", "ModuleNotFoundError when src/app.py is missing")
        check = self.plan()["phases"][0]["acceptance_checks"][0]
        self.assertEqual(check["expect"], "exit 0")
        calibration = check["calibration"]
        self.assertTrue(calibration["executed"])
        self.assertEqual(calibration["exit_code"], 0)
        self.assertIn("VALUE 1", calibration["digest"])
        self.assertEqual(calibration["failure_signature"], "ModuleNotFoundError when src/app.py is missing")
        self.assertEqual(calibration["tree"], self.head[:12])

    def test_red_today_is_recorded_with_the_flag_as_reason_and_printed(self):
        _, out, _ = self.bounded("--check", "python3 -c 'import src.flags'", "--failure", "src/flags.py is this task's new file")
        calibration = self.plan()["phases"][0]["acceptance_checks"][0]["calibration"]
        self.assertEqual(calibration["exit_code"], 1)
        self.assertEqual(calibration["red_reason"], "src/flags.py is this task's new file")
        self.assertNotIn("failure_signature", calibration)
        self.assertIn("red today", out)
        self.assertIn("ModuleNotFoundError", out)

    def test_zero_work_green_is_refused(self):
        _, _, err = self.bounded("--check", "echo 'No tests found'", "--failure", "exit 1 when a test fails", expect=1)
        self.assertIn("zero-work", err)
        self.assertIsNone(self.task()["plan"])

    def test_zero_work_is_searched_in_the_whole_output_not_the_digest(self):
        long_output = "python3 -c \"print('No tests found'); [print('line', i) for i in range(20)]\""
        _, _, err = self.bounded("--check", long_output, "--failure", "exit 1 when a test fails", expect=1)
        self.assertIn("zero-work", err)

    def test_dirty_tree_is_recorded(self):
        self.write("src/app.py", "VALUE = 2\n")
        self.bounded("--check", "true", "--failure", "never green when the shell is broken")
        self.assertEqual(self.plan()["phases"][0]["acceptance_checks"][0]["calibration"]["tree"], self.head[:12] + "+dirty")

    def test_timeout_refuses_the_plan(self):
        _, _, err = self.bounded("--check", "python3 -c 'import time; time.sleep(3)'", "--failure", "n/a", "--check-timeout", "1", expect=1)
        self.assertIn("timed out", err)
        self.assertIsNone(self.task()["plan"])

    def test_amend_check_is_run_too(self):
        self.bounded("--check", "true", "--failure", "never green when the shell is broken")
        _, _, err = self.ai("plan", "amend", "--phase", "1", "--reason", "r", "--check", "true", expect=2)
        self.assertIn("--failure", err)
        self.ai("plan", "amend", "--phase", "1", "--reason", "r", "--check", "python3 -c 'import src.app'", "--failure", "ModuleNotFoundError when src/app.py is missing")
        checks = self.plan()["phases"][0]["acceptance_checks"]
        self.assertEqual(len(checks), 2)
        self.assertEqual(checks[1]["calibration"]["exit_code"], 0)
        self.assertEqual(checks[1]["calibration"]["failure_signature"], "ModuleNotFoundError when src/app.py is missing")

    def test_scope_skipped_runs_the_design_checks_and_warns(self):
        design = self.write(".ai-team/designs/2026-09-05-demo.md", DESIGN_ES.format(security="not-needed", security_body="No aplica."))
        self.ai("new", "2026-09-05-demo", "--kind", "large", "--design", design)
        self.ai("design", "approve", design)
        _, out, _ = self.ai("plan", "generate", "--scope-skipped", "covered by the map")
        phases = self.plan()["phases"]
        red = phases[0]["acceptance_checks"][0]["calibration"]
        self.assertEqual(red["exit_code"], 1)
        self.assertIsNone(red["red_reason"])
        green = phases[1]["acceptance_checks"][0]["calibration"]
        self.assertEqual(green["exit_code"], 0)
        self.assertIsNone(green["failure_signature"])
        self.assertIn("red today", out)
        self.assertIn("scope skipped", out)


class Legacy(unittest.TestCase):
    def test_pre_schema_plan_still_renders(self):
        from ai_team.plan import render_phase, render_plan
        plan = {"kind": "plan", "task": "t", "generated_at": "now", "design": None, "scope_report": None, "title": "t",
                "objective": "o", "constraints": [], "out_of_scope": [],
                "phases": [{"n": 1, "title": "p", "objective": "o", "scenarios": [],
                            "acceptance_checks": [{"command": "true", "expect": "exit 0", "verified": "from the design"}],
                            "expected_files": [], "allowed_edit_roots": [], "scout_notes": [], "open_questions": [], "amendments": []}]}
        self.assertIn("uncalibrated (pre-schema)", render_plan(plan))
        self.assertIn("uncalibrated (pre-schema)", render_phase(plan, 1, "plan.md"))


class ZeroWork(unittest.TestCase):
    def test_signatures(self):
        from ai_team.calibration import zero_work_signature
        for text in ("No tests found, exiting with code 1", "No tests executed!", "psalm: No files analyzed",
                     "Tests:       0 total", "0 files analyzed", "No test files found", "nothing to analyze"):
            self.assertIsNotNone(zero_work_signature(text), text)
        for text in ("Tests: 12 passed, 0 failed", "OK (10 tests, 25 assertions)", "5275 files, No errors found!"):
            self.assertIsNone(zero_work_signature(text), text)


if __name__ == "__main__":
    unittest.main()
