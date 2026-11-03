"""The project's declared test layout: `strict_tdd` and `structure.test_mirror` read from
`.ai-team/config.yaml`, and the path rewrite one mirror rule performs. The convention is
declared, never inferred: no key, no rules; a malformed block names its line."""

import os
import shutil
import tempfile
import unittest

import helpers  # noqa: F401  (puts the machine on sys.path)
from ai_team.config import MirrorRule, load_config, mirror_path
from ai_team.store import MachineError

PHP_RULE = MirrorRule(source="src/", tests="tests/Unit/", prefix="", suffix="Test")
PYTHON_RULE = MirrorRule(source="app/", tests="tests/", prefix="test_", suffix="")
SPEC_RULE = MirrorRule(source="lib/", tests="spec/", prefix="", suffix="_spec")

CONFIG_WITH_MIRRORS = """\
project: demo
strict_tdd: true   # the orchestrator sends the directive

structure:
  source: "src/"
  tests: "tests/"
  test_mirror:
    # one rule per source tree
    - source: "src/"
      tests: "tests/Unit/"
      suffix: "Test"
    - source: app
      tests: ./tests
      prefix: test_   # python style

architecture:
  style: modular
"""


class ConfigCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ai-team-config-")
        self.addCleanup(shutil.rmtree, self.root, True)
        os.makedirs(os.path.join(self.root, ".ai-team"))

    def config(self, text):
        with open(os.path.join(self.root, ".ai-team", "config.yaml"), "w", encoding="utf-8") as handle:
            handle.write(text)
        return load_config(self.root)


class ReadsTheDeclaredConvention(ConfigCase):
    def test_a_config_with_the_key_yields_its_rules_in_order(self):
        config = self.config(CONFIG_WITH_MIRRORS)
        self.assertTrue(config.strict_tdd)
        self.assertEqual(config.mirror_rules, (PHP_RULE, PYTHON_RULE))
        self.assertEqual(config.root, self.root)

    def test_a_config_without_the_key_yields_no_rules(self):
        config = self.config('strict_tdd: true\nstructure:\n  source: "src/"\n  tests: "tests/"\n')
        self.assertTrue(config.strict_tdd)
        self.assertEqual(config.mirror_rules, ())

    def test_a_missing_config_is_not_strict_and_has_no_rules(self):
        config = load_config(self.root)
        self.assertFalse(config.strict_tdd)
        self.assertEqual(config.mirror_rules, ())

    def test_strict_tdd_false_or_commented_out_is_off(self):
        self.assertFalse(self.config("strict_tdd: false\n").strict_tdd)
        self.assertFalse(self.config("# strict_tdd: true\n").strict_tdd)
        self.assertFalse(self.config("structure:\n  strict_tdd: true\n").strict_tdd)

    def test_a_null_or_empty_strict_tdd_reads_as_absent(self):
        for text in ("strict_tdd: ~\n", "strict_tdd:\n", "strict_tdd: null\n", "strict_tdd:   # unset\n"):
            self.assertFalse(self.config(text).strict_tdd, text)

    def test_a_test_mirror_key_outside_structure_is_ignored(self):
        config = self.config('other:\n  test_mirror:\n    - source: "src/"\n      tests: "t/"\n')
        self.assertEqual(config.mirror_rules, ())

    def test_a_plain_structure_block_declares_no_mirror(self):
        config = self.config('''structure:
  source: "domain/skills/"
  tests: "scripts/tests/"
  components: ~
  scripts: "scripts/"
''')
        self.assertEqual(config.mirror_rules, ())
        self.assertFalse(config.strict_tdd)

    def test_an_empty_test_mirror_value_yields_no_rules(self):
        self.assertEqual(self.config("structure:\n  test_mirror: ~\n  tests: x\n").mirror_rules, ())
        self.assertEqual(self.config("structure:\n  test_mirror: []\n").mirror_rules, ())


class RefusesAMalformedBlock(ConfigCase):
    def assertMalformed(self, text, *fragments):
        with self.assertRaises(MachineError) as caught:
            self.config(text)
        message = str(caught.exception)
        for fragment in fragments:
            self.assertIn(fragment, message)

    def test_a_rule_without_tests_names_its_line(self):
        self.assertMalformed("structure:\n  test_mirror:\n    - source: src/\n", "config.yaml:3", "tests")

    def test_a_rule_without_source_names_its_line(self):
        self.assertMalformed("structure:\n  test_mirror:\n    - tests: t/\n    - source: a/\n      tests: b/\n", "config.yaml:3", "source")

    def test_an_unknown_rule_key_names_its_line(self):
        self.assertMalformed("structure:\n  test_mirror:\n    - source: src/\n      tests: t/\n      sufix: Test\n", "config.yaml:5", "sufix")

    def test_a_flow_style_item_names_its_line(self):
        self.assertMalformed('structure:\n  test_mirror:\n    - {source: "src/", tests: "t/"}\n', "config.yaml:3")

    def test_a_scalar_instead_of_a_list_names_its_line(self):
        self.assertMalformed("structure:\n  test_mirror: src/\n", "config.yaml:2", "list")

    def test_a_line_that_is_not_a_rule_item_names_its_line(self):
        self.assertMalformed("structure:\n  test_mirror:\n    source: src/\n", "config.yaml:3")

    def test_an_empty_source_names_its_line(self):
        self.assertMalformed('structure:\n  test_mirror:\n    - source: ""\n      tests: t/\n', "config.yaml:3", "source")

    def test_a_tests_directory_that_is_the_root_names_its_line(self):
        self.assertMalformed("structure:\n  test_mirror:\n    - source: src/\n      tests: .\n", "config.yaml:4", "tests")

    def test_a_non_boolean_strict_tdd_names_its_line(self):
        self.assertMalformed("project: x\nstrict_tdd: maybe\n", "config.yaml:2", "strict_tdd")
        self.assertMalformed("strict_tdd: yes-please\n", "config.yaml:1", "strict_tdd")


class ReadsARootSource(ConfigCase):
    def test_a_dot_or_dot_slash_source_is_the_project_root(self):
        for source in (".", "./", '"."'):
            config = self.config("structure:\n  test_mirror:\n    - source: %s\n      tests: tests/\n      prefix: test_\n" % source)
            self.assertEqual(config.mirror_rules, (MirrorRule(source="", tests="tests/", prefix="test_", suffix=""),), source)
            self.assertEqual(mirror_path("a/b.py", config.mirror_rules), "tests/a/test_b.py")


class RewritesAPathThroughOneRule(unittest.TestCase):
    def test_a_stem_suffix_keeps_the_extension(self):
        self.assertEqual(mirror_path("src/A/B/C.php", [PHP_RULE]), "tests/Unit/A/B/CTest.php")

    def test_a_stem_prefix_keeps_the_extension(self):
        self.assertEqual(mirror_path("app/x.py", [PYTHON_RULE]), "tests/test_x.py")
        self.assertEqual(mirror_path("app/pkg/y.py", [PYTHON_RULE]), "tests/pkg/test_y.py")

    def test_the_rewrite_names_no_extension(self):
        self.assertEqual(mirror_path("lib/a/b.rb", [SPEC_RULE]), "spec/a/b_spec.rb")
        self.assertEqual(mirror_path("lib/a/b.xyz", [SPEC_RULE]), "spec/a/b_spec.xyz")
        self.assertEqual(mirror_path("lib/a/Makefile", [SPEC_RULE]), "spec/a/Makefile_spec")

    def test_a_path_matching_no_rule_has_no_mirror(self):
        self.assertIsNone(mirror_path("config/app.yaml", [PHP_RULE, PYTHON_RULE]))
        self.assertIsNone(mirror_path("srcfoo/x.php", [PHP_RULE]))
        self.assertIsNone(mirror_path("README.md", [PHP_RULE]))

    def test_the_first_matching_rule_wins(self):
        broad = MirrorRule(source="src/", tests="other/", prefix="", suffix="")
        self.assertEqual(mirror_path("src/a.php", [PHP_RULE, broad]), "tests/Unit/aTest.php")
        self.assertEqual(mirror_path("src/a.php", [broad, PHP_RULE]), "other/a.php")

    def test_a_root_source_matches_every_path(self):
        root_rule = MirrorRule(source="", tests="tests/", prefix="test_", suffix="")
        self.assertEqual(mirror_path("a/b.py", [root_rule]), "tests/a/test_b.py")
        self.assertEqual(mirror_path("top.py", [root_rule]), "tests/test_top.py")
        self.assertIsNone(mirror_path("tests/a/test_b.py", [root_rule]))

    def test_a_leading_dot_slash_is_normalized(self):
        self.assertEqual(mirror_path("./src/a.php", [PHP_RULE]), "tests/Unit/aTest.php")

    def test_a_mirror_is_not_mirrored_again(self):
        nested = MirrorRule(source="app/", tests="app/tests/", prefix="test_", suffix="")
        self.assertIsNone(mirror_path("app/tests/test_x.py", [nested]))
        self.assertEqual(mirror_path("app/x.py", [nested]), "app/tests/test_x.py")


if __name__ == "__main__":
    unittest.main()
