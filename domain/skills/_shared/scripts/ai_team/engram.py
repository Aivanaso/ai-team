"""Engram is a mirror, never a store: three verbs leave a searchable memory as a side effect.

Best-effort by contract: no binary on PATH, a non-zero exit or a slow call prints one
warning and the verb still succeeds. Nothing is ever read back from engram to decide.
"""

import shutil
import subprocess
import sys

TIMEOUT_SECONDS = 5
WARNING = "ai-team: engram not available, nothing mirrored (%s)"


def mirror(title, content, memory_type, cwd):
    binary = shutil.which("engram")
    if binary is None:
        sys.stderr.write(WARNING % "binary not on PATH" + "\n")
        return False
    try:
        completed = subprocess.run(
            [binary, "save", title, content, "--type", memory_type],
            cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        sys.stderr.write(WARNING % type(exc).__name__ + "\n")
        return False
    if completed.returncode != 0:
        sys.stderr.write(WARNING % ("exit %d" % completed.returncode) + "\n")
        return False
    return True
