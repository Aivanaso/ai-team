"""Shared helpers for the ai-team machine tests: a throwaway git project with .ai-team/."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(REPO_ROOT, "domain", "skills", "_shared", "scripts")
AI_TEAM = os.path.join(SCRIPTS, "ai-team")
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")

sys.path.insert(0, SCRIPTS)


def run(*args, root=None, cwd=None, env=None, stdin=None):
    """Run the CLI; returns (exit_code, stdout, stderr)."""
    command = [AI_TEAM]
    if root is not None:
        command += ["--root", root]
    command += [str(a) for a in args]
    completed = subprocess.run(command, cwd=cwd or root or REPO_ROOT, env=env, input=stdin,
                               capture_output=True, text=True, check=False)
    return completed.returncode, completed.stdout, completed.stderr


class ProjectCase(unittest.TestCase):
    """A temp git repo with .ai-team/, one tracked file and a HEAD commit; engram hidden from PATH."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ai-team-test-")
        self.addCleanup(shutil.rmtree, self.root, True)
        os.makedirs(os.path.join(self.root, ".ai-team"))
        os.makedirs(os.path.join(self.root, "src"))
        with open(os.path.join(self.root, "src", "app.py"), "w") as handle:
            handle.write("VALUE = 1\n")
        with open(os.path.join(self.root, "README.md"), "w") as handle:
            handle.write("# demo\n")
        git = ["git", "-C", self.root]
        subprocess.run(git + ["init", "-q"], check=True)
        subprocess.run(git + ["-c", "user.email=t@t", "-c", "user.name=t", "add", "-A"], check=True)
        subprocess.run(git + ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"], check=True)
        self.head = subprocess.run(git + ["rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        with open(os.path.join(self.root, ".git", "info", "exclude"), "a") as handle:
            handle.write(".ai-team/\n.bin/\n__pycache__/\n")  # as a real project's .gitignore does
        # A PATH with python3 and git but no engram: the mirror must degrade to one warning.
        bindir = os.path.join(self.root, ".bin")
        os.makedirs(bindir)
        for tool in ("python3", "git", "readlink", "dirname", "bash", "env"):
            found = shutil.which(tool)
            if found:
                os.symlink(found, os.path.join(bindir, tool))
        self.env = dict(os.environ, PATH=bindir)

    def ai(self, *args, expect=0, stdin=None):
        code, out, err = run(*args, root=self.root, env=self.env, stdin=stdin)
        if expect is not None:
            self.assertEqual(code, expect, "ai-team %s\nstdout:\n%s\nstderr:\n%s" % (" ".join(map(str, args)), out, err))
        return code, out, err

    def task(self):
        tasks_dir = os.path.join(self.root, ".ai-team", "tasks")
        files = sorted(f for f in os.listdir(tasks_dir) if f.endswith(".json"))
        with open(os.path.join(tasks_dir, files[-1])) as handle:
            return json.load(handle)

    def ticket_by_id(self, ticket_id):
        return next(t for t in self.task()["tickets"] if t["id"] == ticket_id)

    def write(self, rel, text):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return rel

    def read(self, rel):
        with open(os.path.join(self.root, rel), encoding="utf-8") as handle:
            return handle.read()

    def plan(self):
        """The plan object the machine reads back: the final json block of the plan file."""
        return json.loads(self.read(self.task()["plan"]).split("```json\n")[1].split("\n```")[0])


def receipt_block(obj):
    return "# Review Report\n\nprose\n\n## Receipt\n\n```json\n%s\n```\n" % json.dumps(obj, indent=2)


def full_receipt(findings=(), verdict=None, tier=1, closed=None, verdict_history=None):
    critical = any(f.get("severity") == "CRITICAL" for f in findings)
    receipt = {
        "tier": tier,
        "tier_reason": "tier %d: test" % tier,
        "verdict": verdict or ("review-blocked" if critical else "review-clear"),
        "lenses": {"correctness": {"status": "findings" if findings else "pass", "findings": list(findings)}},
        "verification": [{"command": "true", "exit_code": 0, "outcome": "pass"}],
    }
    if closed is not None:
        receipt["closed"] = closed
    if verdict_history is not None:
        receipt["verdict_history"] = verdict_history
    return receipt


def fragment(findings=(), closed=None):
    frag = {
        "kind": "security-fragment",
        "tier": 2,
        "tier_reason": "tier 2: test",
        "lenses": {"security": {"status": "findings" if findings else "pass", "findings": list(findings)}},
    }
    if closed is not None:
        frag["closed"] = closed
    return frag


def finding(fid, severity="MINOR", file="src/app.py", evidence="read", trigger=None):
    entry = {"id": fid, "severity": severity, "confidence": "high", "evidence": evidence,
             "file": file, "line": 1, "claim": "%s claim" % fid}
    if trigger or (severity != "MINOR" and evidence == "read"):
        entry["trigger"] = trigger or "input X reaches line 1"
    return entry


DESIGN_ES = """---
title: "Flag de ejemplo"
created_at: "2026-09-05T10:00:00Z"
status: draft
map_report: ".ai-team/explorations/2026-09-05-demo-map.md"
security: {security}
---
## Objetivo

Añadir un flag que apague la función sin tocar el resto.

## Contexto

`src/app.py:1` define VALUE.

## Decisiones

- El flag está apagado por defecto; con el flag apagado el comportamiento actual no cambia.
- Un valor de flag no reconocido se rechaza, nunca se interpreta.

## Diseño

### Superficies nombradas

- `src/app.py:1` — donde vive VALUE
- `src/flags.py` (nueva) — el flag

## Seguridad

{security_body}

## Fuera de alcance

- Persistir el flag

## Fases

### Fase 1 — El flag existe
Entrega: `src/flags.py` con el flag y su lectura.
Escenarios:
- Dado ningún flag, cuando se lee, entonces devuelve apagado.
- Dado un valor desconocido, cuando se lee, entonces se rechaza.
Check: `python3 -c "import src.flags"`

### Fase 2 — VALUE respeta el flag
Entrega: `src/app.py` consulta el flag.
Escenarios:
- Dado el flag apagado, cuando se calcula VALUE, entonces vale 1.
Check: `python3 -c "import src.app"`
"""

SCOPE_REPORT = """# Scope report

prose

```json
{"kind": "scope-report", "phases": [
  {"n": 1, "expected_files": [{"action": "CREATE", "path": "src/flags.py", "evidence": "src/app.py:1"}],
   "acceptance_checks": [{"command": "python3 -c 'import src.flags'", "expect": "exit 0",
                          "calibration": {"executed": true, "exit_code": 1, "digest": "ModuleNotFoundError: No module named 'src.flags'",
                                          "red_reason": "src/flags.py is this phase's CREATE file"}}],
   "constraints_candidates": ["src/app.py:1 -- VALUE is read at import time"], "open_questions": []},
  {"n": 2, "expected_files": [{"action": "MODIFY", "path": "src/app.py", "evidence": "src/app.py:1"}],
   "acceptance_checks": [{"command": "python3 -c 'import src.app'", "expect": "exit 0",
                          "calibration": {"executed": true, "exit_code": 0, "digest": "(no output)",
                                          "failure_signature": "ModuleNotFoundError when src/app.py is missing"}}],
   "constraints_candidates": [], "open_questions": []}
]}
```
"""


STRICT_UNIT_MIRROR = """strict_tdd: true
structure:
  test_mirror:
    - source: "src/"
      tests: "tests/Unit/"
      suffix: "Test"
"""

STRICT_PREFIX_MIRROR = """strict_tdd: true
structure:
  test_mirror:
    - source: "src/"
      tests: "tests/"
      prefix: "test_"
"""

STRICT_WITHOUT_MIRROR = "strict_tdd: true\n"


def scope_report_listing(phase1_files, phase2_files=("src/app.py",)):
    """A scope report whose two phases name only the given files (action CREATE for phase 1, MODIFY for phase 2)."""
    def entry(n, action, paths):
        return {"n": n, "expected_files": [{"action": action, "path": p, "evidence": "src/app.py:1"} for p in paths],
                "acceptance_checks": [{"command": "true", "expect": "exit 0",
                                       "calibration": {"executed": True, "exit_code": 0, "digest": "(no output)",
                                                       "failure_signature": "never red: a no-op"}}],
                "constraints_candidates": [], "open_questions": []}
    report = {"kind": "scope-report", "phases": [entry(1, "CREATE", phase1_files), entry(2, "MODIFY", phase2_files)]}
    return "# Scope report\n\nprose\n\n```json\n%s\n```\n" % json.dumps(report)
