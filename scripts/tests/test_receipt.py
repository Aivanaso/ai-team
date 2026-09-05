"""Calibration suite of the receipt validator (`ai-team receipt check`), inherited from
check-receipt.py: every known-negative fixture must exit 1 (or 2 when validation cannot run),
so the checks are proven able to fail before their green counts (evidence-protocol Rule 7).
"""

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
]
EXIT_1_SINGLE_VIOLATION = ["receipt-md-no-block", "receipt-md-two-blocks", "receipt-md-malformed-block", "receipt-md-wrong-fence-label"]
EXIT_2 = ["receipt-not-utf8", "receipt-top-level-array"]
EXIT_0 = ["receipt-good", "receipt-verification-omitted-with-reason", "receipt-security-fragment-good",
          "receipt-md-block-good", "receipt-md-prose-fence-string"]

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


class Generated(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ai-team-receipt-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _write(self, name, text):
        path = os.path.join(self.tmp, name)
        with open(path, "w") as handle:
            handle.write(text)
        return path

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
