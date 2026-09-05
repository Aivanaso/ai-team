#!/usr/bin/env python3
"""check-receipt.py -- compatibility shim. The validator now lives in the ai-team machine:

    ai-team receipt check <report.md> [project_root]

`receipt <file.md> [project_root]` is forwarded there. The ledger mode and the `--legacy`
bare-JSON container are gone with the Brief File (design note 2026-09-05 §7).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_team.cli import main  # noqa: E402

if __name__ == "__main__":
    argv = sys.argv[1:]
    if argv and argv[0] == "receipt" and "--legacy" not in argv:
        sys.exit(main(["receipt", "check"] + argv[1:]))
    sys.stderr.write("check-receipt.py: use `ai-team receipt check <report.md> [project_root]`; ledger mode and --legacy no longer exist\n")
    sys.exit(2)
