"""merge-hooks.py: registers the machine's two hooks inside a user-owned settings.json without
touching anything else, idempotently, with a backup, and undoes itself with --remove."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

from helpers import REPO_ROOT

MERGE = os.path.join(REPO_ROOT, "adapters", "claude-code", "merge-hooks.py")
TEMPLATE = os.path.join(REPO_ROOT, "adapters", "claude-code", "templates", "hooks.json")

FOREIGN = {
    "permissions": {"allow": ["Read"], "defaultMode": "auto"},
    "model": "fable",
    "hooks": {
        "Stop": [{"hooks": [{"type": "command", "command": "bash notify.sh done"}]}],
        "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "bash my-own-guard.sh"}]}],
    },
}


def merge(settings_path, *extra):
    return subprocess.run(["python3", MERGE, settings_path, TEMPLATE, *extra], capture_output=True, text=True, check=False)


class MergeHooks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ai-team-merge-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.settings = os.path.join(self.tmp, "settings.json")
        with open(self.settings, "w") as handle:
            json.dump(FOREIGN, handle, indent=2)

    def _load(self):
        with open(self.settings) as handle:
            return json.load(handle)

    def _ours(self, data):
        return [h for groups in data["hooks"].values() for g in groups for h in g["hooks"] if "_shared/scripts/ai-team" in h["command"]]

    def test_merge_keeps_foreign_content_and_adds_two_hooks(self):
        result = merge(self.settings)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self._load()
        self.assertEqual(data["permissions"], FOREIGN["permissions"])
        self.assertEqual(data["model"], "fable")
        self.assertEqual(data["hooks"]["Stop"], FOREIGN["hooks"]["Stop"])
        self.assertEqual(data["hooks"]["PreToolUse"][0], FOREIGN["hooks"]["PreToolUse"][0])
        ours = self._ours(data)
        self.assertEqual(len(ours), 2)
        self.assertTrue(any("pre-tool-use" in h["command"] for h in ours))
        self.assertTrue(any("session-start" in h["command"] for h in ours))
        self.assertEqual(data["hooks"]["SessionStart"][0]["matcher"], "startup|clear|compact")
        backups = [f for f in os.listdir(self.tmp) if f.startswith("settings.json.bak-")]
        self.assertEqual(len(backups), 1)

    def test_idempotent(self):
        merge(self.settings)
        first = open(self.settings).read()
        merge(self.settings)
        self.assertEqual(open(self.settings).read(), first)
        self.assertEqual(len(self._ours(self._load())), 2)

    def test_remove_restores_foreign_shape(self):
        merge(self.settings)
        result = merge(self.settings, "--remove")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self._load()
        self.assertEqual(data["hooks"], FOREIGN["hooks"])
        self.assertNotIn("SessionStart", data["hooks"])

    def test_creates_settings_when_absent(self):
        os.remove(self.settings)
        result = merge(self.settings)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self._ours(self._load())), 2)

    def test_malformed_settings_left_unchanged(self):
        with open(self.settings, "w") as handle:
            handle.write("{not json")
        result = merge(self.settings)
        self.assertEqual(result.returncode, 1)
        self.assertIn("not valid JSON", result.stderr)
        self.assertEqual(open(self.settings).read(), "{not json")


if __name__ == "__main__":
    unittest.main()
