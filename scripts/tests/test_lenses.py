"""The two review lenses run one after the other on one working tree, and the tree they
audit is the tree the implementer settled: the machine fingerprints it at the implementer's
settle and refuses a lens settle when the fingerprint moved (a mutation probe that was not
restored, a build artifact left behind). Known negatives first."""

import json
import os
import re
import unittest

from helpers import ProjectCase, full_receipt, receipt_block


class LensCase(ProjectCase):
    def setUp(self):
        super().setUp()
        self.ai("new", "demo", "--kind", "bounded")
        self.ai("plan", "generate", "--objective", "x", "--file", "src/app.py", "--check", "true",
                "--failure", "never green when the shell is broken")
        self.ai("acquire", "implementer", "--phase", "1")
        self.ai("settle", "t1", "--outcome", "ok", "--model", "sonnet", "--tokens", "1", "--tool-uses", "1", "--duration", "1")
        self.ai("tier", "2", "--phase", "1", "--reason", "parses untrusted input")

    def settle_lens(self, ticket, expect=0, findings=()):
        report = self.write(".ai-team/reviews/%s.md" % ticket, receipt_block(full_receipt(findings, tier=2)))
        return self.ai("settle", ticket, "--outcome", "ok", "--model", "sonnet", "--tokens", "1", "--tool-uses", "1", "--duration", "1",
                       "--report", report, expect=expect)

    def ticket(self, tid):
        return [t for t in self.task()["tickets"] if t["id"] == tid][0]


class OneLensAtATime(LensCase):
    def test_security_waits_for_the_reviewer_to_settle(self):
        self.ai("acquire", "reviewer", "--phase", "1")
        _, _, err = self.ai("acquire", "security-audit", "--phase", "1", expect=1)
        self.assertIn("t2 (reviewer) is open", err)
        self.settle_lens("t2")
        self.ai("acquire", "security-audit", "--phase", "1")

    def test_reviewer_waits_for_security_too(self):
        self.ai("acquire", "security-audit", "--phase", "1")
        _, _, err = self.ai("acquire", "reviewer", "--phase", "1", expect=1)
        self.assertIn("t2 (security-audit) is open", err)


class PriorReportHint(ProjectCase):
    """Attempt ≥ 2 of a lens: the machine says whether an earlier report exists, so the
    reviewer runs a delta pass over it or a full pass with `prior_report: none` -- and never
    blocks on a path nobody could have injected (ECO-1267 retro F3)."""

    def setUp(self):
        super().setUp()
        self.ai("new", "demo", "--kind", "bounded")
        self.ai("plan", "generate", "--objective", "x", "--file", "src/app.py", "--check", "true",
                "--failure", "never green when the shell is broken")

    def implement(self, outcome):
        _, out, _ = self.ai("acquire", "implementer", "--phase", "1")
        self.ai("settle", out.split()[1], "--outcome", outcome, "--model", "sonnet", "--tokens", "1", "--tool-uses", "1", "--duration", "1")

    def test_first_attempt_never_reached_review_so_the_second_is_a_full_pass(self):
        self.implement("needs_input")
        self.implement("ok")
        self.ai("tier", "1", "--phase", "1", "--reason", "code")
        _, out, _ = self.ai("acquire", "reviewer", "--phase", "1")
        self.assertIn("attempt 2: full pass", out)
        self.assertIn("attempt 1 settled needs_input", out)
        self.assertIn("prior_report: none", out)

    def test_an_earlier_report_makes_the_second_attempt_a_delta_pass(self):
        self.implement("ok")
        self.ai("tier", "1", "--phase", "1", "--reason", "code")
        _, out, _ = self.ai("acquire", "reviewer", "--phase", "1")
        self.assertNotIn("attempt 1:", out)  # a first lens pass carries no hint
        report = self.write(".ai-team/reviews/t2.md", receipt_block(full_receipt(
            [{"id": "F-1", "severity": "CRITICAL", "confidence": "high", "evidence": "executed", "file": "src/app.py", "line": 1, "claim": "c"}])))
        self.ai("settle", "t2", "--outcome", "ok", "--model", "sonnet", "--tokens", "1", "--tool-uses", "1", "--duration", "1", "--report", report)
        self.implement("ok")
        _, out, _ = self.ai("acquire", "reviewer", "--phase", "1")
        self.assertIn("attempt 2: delta pass", out)
        self.assertIn(".ai-team/reviews/t2.md", out)


class LedgerNotIgnored(LensCase):
    """A project that does not gitignore .ai-team/: the machine's own writes between two
    settles (task JSON, tier, the lens report) are never counted as a moved tree."""

    def setUp(self):
        super().setUp()
        with open(os.path.join(self.root, ".git", "info", "exclude"), "w") as handle:
            handle.write(".bin/\n__pycache__/\n")
        # re-settle a fresh implementer attempt under the new ignore rules
        self.ai("acquire", "reviewer", "--phase", "1")
        report = self.write(".ai-team/reviews/t2.md", receipt_block(full_receipt(
            [{"id": "F-1", "severity": "CRITICAL", "confidence": "high", "evidence": "executed", "file": "src/app.py", "line": 1, "claim": "c"}], tier=2)))
        self.ai("settle", "t2", "--outcome", "ok", "--model", "sonnet", "--tokens", "1", "--tool-uses", "1", "--duration", "1", "--report", report)
        self.ai("acquire", "implementer", "--phase", "1")
        self.ai("settle", "t3", "--outcome", "ok", "--model", "sonnet", "--tokens", "1", "--tool-uses", "1", "--duration", "1")

    def test_machine_writes_under_ai_team_do_not_move_the_tree(self):
        self.ai("acquire", "reviewer", "--phase", "1")
        # attempt 2: F-1 (CRITICAL, t2) re-listed -- still open, not this test's concern
        self.settle_lens("t4", findings=[
            {"id": "F-1", "severity": "CRITICAL", "confidence": "high", "evidence": "executed", "file": "src/app.py", "line": 1, "claim": "c"}])
        self.assertEqual(self.ticket("t4")["tree"], self.ticket("t3")["tree"])


class TreeFingerprint(LensCase):
    def test_implementer_settle_records_the_tree(self):
        tree = self.ticket("t1")["tree"]
        self.assertTrue(re.fullmatch(r"[0-9a-f]{40}", tree or ""), tree)

    def test_lens_settle_refuses_a_tree_that_moved(self):
        self.ai("acquire", "reviewer", "--phase", "1")
        self.write("src/app.py", "VALUE = 1\nMUTATED = True\n")
        _, _, err = self.settle_lens("t2", expect=1)
        self.assertIn("working tree changed", err)
        self.assertIn("src/app.py", err)
        self.assertIn("stays open", err)
        self.assertIn("git cat-file blob %s:'src/app.py' > 'src/app.py'" % self.ticket("t1")["tree"], err)
        self.assertIsNone(self.ticket("t2")["settled_at"])
        # the probe is restored byte for byte: the same settle now closes the ticket
        self.write("src/app.py", "VALUE = 1\n")
        self.settle_lens("t2")
        self.assertEqual(self.ticket("t2")["tree"], self.ticket("t1")["tree"])

    def test_a_new_untracked_file_counts_as_a_move(self):
        self.ai("acquire", "reviewer", "--phase", "1")
        self.write("src/probe.py", "x = 1\n")
        _, _, err = self.settle_lens("t2", expect=1)
        self.assertIn("src/probe.py", err)
        self.assertIn("rm -- 'src/probe.py'", err)

    def test_files_the_project_ignores_do_not_count(self):
        self.ai("acquire", "reviewer", "--phase", "1")
        self.write("src/__pycache__/app.cpython.pyc", "bytes")  # ignored by the project's rules
        self.write(".ai-team/reviews/scratch.md", "notes")
        self.settle_lens("t2")

    def test_the_implementer_tree_is_what_the_lens_sees_even_across_attempts(self):
        # attempt 2's implementer changes the file legitimately; the lens compares against attempt 2's tree
        self.ai("acquire", "reviewer", "--phase", "1")
        report = self.write(".ai-team/reviews/t2.md", receipt_block(full_receipt(
            [{"id": "F-1", "severity": "CRITICAL", "confidence": "high", "evidence": "executed", "file": "src/app.py", "line": 1, "claim": "c"}], tier=2)))
        self.ai("settle", "t2", "--outcome", "ok", "--model", "sonnet", "--tokens", "1", "--tool-uses", "1", "--duration", "1", "--report", report)
        self.ai("acquire", "implementer", "--phase", "1")
        self.write("src/app.py", "VALUE = 2\n")
        self.ai("settle", "t3", "--outcome", "ok", "--model", "sonnet", "--tokens", "1", "--tool-uses", "1", "--duration", "1")
        self.assertNotEqual(self.ticket("t3")["tree"], self.ticket("t1")["tree"])
        self.ai("acquire", "reviewer", "--phase", "1")
        # attempt 2: F-1 (CRITICAL, t2) re-listed -- still open, not this test's concern
        self.settle_lens("t4", findings=[
            {"id": "F-1", "severity": "CRITICAL", "confidence": "high", "evidence": "executed", "file": "src/app.py", "line": 1, "claim": "c"}])

    def test_legacy_implementer_ticket_without_a_tree_is_not_compared(self):
        path = os.path.join(self.root, ".ai-team", "tasks", "%s.json" % self.task()["task"])
        with open(path) as handle:
            task = json.load(handle)
        del task["tickets"][0]["tree"]
        with open(path, "w") as handle:
            json.dump(task, handle)
        self.ai("acquire", "reviewer", "--phase", "1")
        self.write("src/app.py", "VALUE = 1\nMUTATED = True\n")
        self.settle_lens("t2")


if __name__ == "__main__":
    unittest.main()
