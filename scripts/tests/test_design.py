"""The design parser: Spanish and English headings, phase blocks, completeness problems."""

import os
import shutil
import tempfile
import unittest

from helpers import DESIGN_ES
from ai_team.design import approve, design_problems, load_design, parse_frontmatter
from ai_team.store import MachineError

DESIGN_EN = """---
title: "Example flag"
status: approved
security: not-needed
---
## Objective

Add a flag.

## Decisions

1. Off by default.

## Design

### Named surfaces

- `src/app.py:1`

## Security

Not applicable: no untrusted input.

## Out of scope

- Persistence

## Phases

### Phase 1 - The flag exists
Delivers: the module.
Scenarios:
- Given nothing, when read, then off.
Checks:
- `python3 -c "import src.flags"`
- `python3 -m compileall src`
"""


class Parser(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ai-team-design-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _write(self, text):
        path = os.path.join(self.tmp, "design.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def test_spanish_headings(self):
        design = load_design(self._write(DESIGN_ES.format(security="not-needed", security_body="No aplica: sin entrada externa.")))
        self.assertEqual(design["status"], "draft")
        self.assertEqual(design["security"], "not-needed")
        self.assertIn("apague", design["objective"])
        self.assertEqual(len(design["decisions"]), 2)
        self.assertEqual(design["security_measures"], [])
        self.assertEqual(design["out_of_scope"], ["Persistir el flag"])
        self.assertEqual([s["path"] for s in design["surfaces"]], ["src/app.py", "src/flags.py"])
        self.assertEqual([s["action"] for s in design["surfaces"]], ["MODIFY", "CREATE"])
        self.assertEqual(len(design["phases"]), 2)
        self.assertEqual(design["phases"][0]["title"], "El flag existe")
        self.assertEqual(len(design["phases"][0]["scenarios"]), 2)
        self.assertEqual(design["phases"][0]["checks"], ['python3 -c "import src.flags"'])
        self.assertEqual(design_problems(design, require_approved=False), [])

    def test_english_headings_and_bulleted_checks(self):
        design = load_design(self._write(DESIGN_EN))
        self.assertEqual(design["decisions"], ["Off by default."])
        self.assertEqual(design["phases"][0]["checks"], ['python3 -c "import src.flags"', "python3 -m compileall src"])
        self.assertEqual(design_problems(design), [])

    def test_security_measures_become_constraint_material(self):
        design = load_design(self._write(DESIGN_ES.format(security="done", security_body="- Rechazar valores fuera de la lista blanca.")))
        self.assertEqual(design["security_measures"], ["Rechazar valores fuera de la lista blanca."])

    def test_problems_named(self):
        text = DESIGN_ES.format(security="pending", security_body="").replace("- El flag", "El flag").replace("- Un valor", "Un valor")
        text = text.replace('Check: `python3 -c "import src.app"`', "Check:")
        problems = design_problems(load_design(self._write(text)))
        joined = "\n".join(problems)
        self.assertIn("status is 'draft'", joined)
        self.assertIn("security: pending", joined)
        self.assertIn("Decisions has no bullet", joined)
        self.assertIn("phase 2 has no Check", joined)

    def test_approve_refuses_pending_security_then_flips(self):
        path = self._write(DESIGN_ES.format(security="pending", security_body=""))
        with self.assertRaises(MachineError):
            approve(path)
        with open(path, encoding="utf-8") as handle:
            text = handle.read().replace("security: pending", "security: not-needed")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        design = approve(path)
        self.assertEqual(design["status"], "approved")
        self.assertTrue(design["approved_at"])
        with open(path, encoding="utf-8") as handle:
            fields, _ = parse_frontmatter(handle.read())
        self.assertEqual(fields["status"], "approved")
        self.assertEqual(fields["title"], "Flag de ejemplo")
        with self.assertRaises(MachineError):
            approve(path)


if __name__ == "__main__":
    unittest.main()
