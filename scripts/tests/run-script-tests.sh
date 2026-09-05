#!/usr/bin/env bash
# scripts/tests/run-script-tests.sh -- the test runner for domain/skills/_shared/scripts/.
#
# Layers (design note 2026-09-05 §15): the machine's unit tests, the receipt calibration
# suite (known negatives first, so a check is proven able to fail), the hook tests fed the
# same JSON Claude Code sends on stdin. No model involved; the orchestrator evals live in
# evals/ and are run by hand or nightly.
#
# Run before any commit that touches domain/skills/_shared/scripts/.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cd "$here"
exec python3 -m unittest discover -s "$here" -p 'test_*.py' -v "$@"
