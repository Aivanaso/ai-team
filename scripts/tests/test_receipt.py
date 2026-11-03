"""Calibration suite of the receipt validator (`ai-team receipt check`), inherited from
check-receipt.py: every known-negative fixture must exit 1 (or 2 when validation cannot run),
so the checks are proven able to fail before their green counts (evidence-protocol Rule 7).
"""

import json
import os
import shutil
import tempfile
import unittest

from helpers import FIXTURES, REPO_ROOT, run

EXIT_1 = [
    "receipt-missing-file", "receipt-line-as-string", "receipt-trigger-missing-major-read",
    "receipt-verdict-mismatch", "receipt-history-mismatch", "receipt-duplicate-ids",
    "receipt-unknown-severity", "receipt-file-not-on-disk", "receipt-not-json", "receipt-file-absolute",
    "receipt-file-traversal", "receipt-file-is-directory", "receipt-correctness-null",
    "receipt-truncated-no-correctness", "receipt-security-fragment-bad-verdict",
    "receipt-lens-status-incoherent", "receipt-tier-bool", "receipt-duplicate-ids-unicode",
    "receipt-history-garbage-entry", "receipt-kind-unknown", "receipt-fragment-with-correctness",
    "receipt-verification-empty", "receipt-verification-garbage", "receipt-not-reverified-garbage",
    "receipt-file-nul", "receipt-verification-reason-with-entries", "receipt-fragment-with-omitted-reason",
    "receipt-closed-and-findings-same-id", "receipt-closed-file-traversal",
    "receipt-major-clear-mismatch", "receipt-critical-gated-mismatch", "receipt-major-blocked-mismatch",
    "receipt-minor-gated-mismatch", "receipt-security-fragment-major-clear",
]
EXIT_1_SINGLE_VIOLATION = ["receipt-md-no-block", "receipt-md-two-blocks", "receipt-md-malformed-block", "receipt-md-wrong-fence-label"]
EXIT_2 = ["receipt-not-utf8", "receipt-top-level-array"]
EXIT_0 = ["receipt-good", "receipt-verification-omitted-with-reason", "receipt-security-fragment-good",
          "receipt-md-block-good", "receipt-md-prose-fence-string",
          "receipt-closed-good", "receipt-closed-on-full-receipt", "receipt-gated-good"]

NEEDS_GATED = "verdict must be 'review-gated' -- 'F-1' is MAJOR and no CRITICAL finding exists in any lens of the receipt"
NEEDS_BLOCKED = "verdict must be 'review-blocked' -- 'F-1' is CRITICAL"
NEEDS_CLEAR = "verdict must be 'review-clear' -- no MAJOR or CRITICAL finding exists in any lens of the receipt"
# One wrong pairing per fixture: the verdict the receipt writes against the one its findings set.
VERDICT_MISMATCHES = {
    "receipt-verdict-mismatch": NEEDS_BLOCKED,                  # CRITICAL written review-clear
    "receipt-critical-gated-mismatch": NEEDS_BLOCKED,           # CRITICAL written review-gated
    "receipt-major-clear-mismatch": NEEDS_GATED,                # MAJOR written review-clear
    "receipt-major-blocked-mismatch": NEEDS_GATED,              # MAJOR written review-blocked
    "receipt-minor-gated-mismatch": NEEDS_CLEAR,                # MINOR written review-gated
    "receipt-security-fragment-major-clear": NEEDS_GATED,       # fragment MAJOR written review-clear
    "receipt-security-fragment-bad-verdict": NEEDS_BLOCKED,     # fragment CRITICAL written review-clear
}

GOOD_BODY = """{
  "tier": 1, "tier_reason": "tier 1: standard code change", "verdict": "review-clear",
  "lenses": {"correctness": {"status": "findings", "findings": [
    {"id": "F-1", "severity": "MINOR", "confidence": "medium", "evidence": "read", "file": "%s", "line": 1, "claim": "c"}]}},
  "verification": [{"command": "true", "exit_code": 0, "outcome": "pass"}]
}"""


def fixture(name):
    return os.path.join(FIXTURES, name + ".md")


def check(path, root=REPO_ROOT):
    return run("receipt", "check", path, root)


def violations(out):
    return [line for line in out.splitlines() if line.startswith("VIOLATION")]


def wrap(body):
    return "# report\n\n```json\n%s\n```\n" % body


class FixtureTable(unittest.TestCase):
    def test_every_fixture_is_asserted(self):
        on_disk = {f[:-3] for f in os.listdir(FIXTURES) if f.endswith(".md")}
        asserted = set(EXIT_1 + EXIT_1_SINGLE_VIOLATION + EXIT_2 + EXIT_0 + ["receipt-degenerate-root-single-violation"])
        self.assertEqual(on_disk, asserted, "fixtures without an assertion, or assertions without a fixture")

    def test_negatives_exit_1(self):
        for name in EXIT_1:
            with self.subTest(name):
                code, out, err = check(fixture(name))
                self.assertEqual(code, 1, out + err)
                self.assertTrue(violations(out), out)

    def test_a_verdict_that_disagrees_with_its_findings_is_refused_with_the_expected_value(self):
        for name, expected in VERDICT_MISMATCHES.items():
            with self.subTest(name):
                code, out, _ = check(fixture(name))
                self.assertEqual(code, 1)
                self.assertEqual(violations(out), ["VIOLATION %s: %s" % (fixture(name), expected)])

    def test_container_negatives_are_one_violation(self):
        for name in EXIT_1_SINGLE_VIOLATION:
            with self.subTest(name):
                code, out, _ = check(fixture(name))
                self.assertEqual(code, 1)
                self.assertEqual(len(violations(out)), 1, out)

    def test_unvalidatable_exit_2(self):
        for name in EXIT_2:
            with self.subTest(name):
                code, out, err = check(fixture(name))
                self.assertEqual(code, 2, out + err)
                self.assertIn("ERROR", err)
                self.assertEqual(out, "")

    def test_positives_exit_0(self):
        for name in EXIT_0:
            with self.subTest(name):
                code, out, err = check(fixture(name))
                self.assertEqual(code, 0, out + err)
                self.assertFalse(violations(out))

    def test_degenerate_root_short_circuits_to_one_violation(self):
        for root in ("/", REPO_ROOT):
            with self.subTest(root):
                code, out, _ = check(fixture("receipt-degenerate-root-single-violation"), root)
                self.assertEqual(code, 1)
                self.assertEqual(len(violations(out)), 1, out)


def receipt_body(correctness, security=None, verdict="review-clear"):
    """A full receipt whose lenses carry one finding per given severity (ids F-1, F-2, ...)."""
    def lens(severities, start):
        findings = [
            {"id": "F-%d" % (start + i), "severity": sev, "confidence": "high", "evidence": "executed",
             "file": "README.md", "line": 1, "claim": "c"}
            for i, sev in enumerate(severities)
        ]
        return {"status": "findings" if findings else "pass", "findings": findings}
    lenses = {"correctness": lens(correctness, 1)}
    if security is not None:
        lenses["security"] = lens(security, 1 + len(correctness))
    return json.dumps({
        "tier": 2, "tier_reason": "tier 2: test", "verdict": verdict, "lenses": lenses,
        "verification": [{"command": "true", "exit_code": 0, "outcome": "pass"}],
    })


class Generated(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ai-team-receipt-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _write(self, name, text):
        path = os.path.join(self.tmp, name)
        with open(path, "w") as handle:
            handle.write(text)
        return path

    def test_the_three_verdicts_each_validate_only_their_own_severity(self):
        severities = {"review-blocked": ["CRITICAL", "MAJOR"], "review-gated": ["MAJOR", "MINOR"], "review-clear": ["MINOR"]}
        for written in severities:
            for expected in severities:
                with self.subTest(written=written, findings=expected):
                    path = self._write("v.md", wrap(receipt_body(severities[expected], verdict=written)))
                    code, out, err = check(path)
                    self.assertEqual(code, 0 if written == expected else 1, out + err)

    def test_the_verdict_reads_every_lens_of_the_receipt(self):
        for written, expected_code in (("review-clear", 1), ("review-gated", 1), ("review-blocked", 0)):
            with self.subTest(written):
                path = self._write("v.md", wrap(receipt_body([], ["CRITICAL"], verdict=written)))
                code, out, err = check(path)
                self.assertEqual(code, expected_code, out + err)
                self.assertNotIn("combines tier-2 verdicts", out)
        path = self._write("v.md", wrap(receipt_body(["MINOR"], ["MAJOR"], verdict="review-gated")))
        self.assertEqual(check(path)[0], 0)

    def test_a_violation_names_the_finding_by_its_id_and_never_quotes_its_claim(self):
        body = json.loads(receipt_body(["MAJOR"]))
        body["lenses"]["correctness"]["findings"][0]["id"] = "F-" + "x" * 300
        body["lenses"]["correctness"]["findings"][0]["claim"] = "SECRET-CLAIM-TEXT"
        code, out, _ = check(self._write("v.md", wrap(json.dumps(body))))
        self.assertEqual(code, 1)
        self.assertNotIn("SECRET-CLAIM-TEXT", out)
        self.assertLess(len(out), 400)

    def test_missing_file_is_exit_2(self):
        code, out, err = check(os.path.join(self.tmp, "never-written.md"))
        self.assertEqual(code, 2)
        self.assertIn("ERROR", err)

    def test_good_receipt_under_degenerate_root_is_one_violation(self):
        path = self._write("good.md", wrap(GOOD_BODY % "README.md"))
        code, out, _ = check(path, "/")
        self.assertEqual(code, 1)
        self.assertEqual(len(violations(out)), 1, out)

    def test_absolute_citation_still_checked_under_degenerate_root(self):
        absolute = os.path.join(REPO_ROOT, "README.md")
        path = self._write("abs.md", wrap(GOOD_BODY % absolute))
        code, out, _ = check(path, "/")
        self.assertEqual(code, 1)
        self.assertEqual(len(violations(out)), 2, out)

    def test_absolute_citation_inside_root_is_rejected(self):
        path = self._write("abs-inside.md", wrap(GOOD_BODY % os.path.join(REPO_ROOT, "README.md")))
        code, out, _ = check(path)
        self.assertEqual(code, 1)
        self.assertIn("absolute paths", out)

    def test_deep_nesting_is_exit_2_not_a_traceback(self):
        path = self._write("deep.md", wrap("[" * 200000 + "]" * 200000))
        code, out, err = check(path)
        self.assertEqual(code, 2)
        self.assertNotIn("Traceback", err)

    def test_symlink_escape_is_a_violation(self):
        fake_root = os.path.join(self.tmp, "fake-root")
        outside = os.path.join(self.tmp, "outside")
        os.makedirs(fake_root)
        os.makedirs(outside)
        open(os.path.join(outside, "elsewhere.txt"), "w").close()
        os.symlink(os.path.join(outside, "elsewhere.txt"), os.path.join(fake_root, "escape-link"))
        path = self._write(os.path.join("fake-root", "report.md"), wrap(GOOD_BODY % "escape-link"))
        code, out, _ = check(path, fake_root)
        self.assertEqual(code, 1)
        self.assertIn("outside project_root", out)

    def test_unterminated_fence_is_one_violation(self):
        path = self._write("open.md", "# r\n\n```json\n{\"tier\": 1}\n")
        code, out, _ = check(path)
        self.assertEqual(code, 1)
        self.assertEqual(len(violations(out)), 1)
        self.assertIn("never closed", out)


if __name__ == "__main__":
    unittest.main()
