"""Calibrated acceptance checks: a check enters a plan only with its calibration on paper.

A calibration says what the command did on the current tree -- exit code and an output
digest -- and one of two things: green today, so how a known failure of it shows
(`failure_signature`); or red today, so why it fails now and that the phase turns it green
(`red_reason`). A check nobody ran (`executed: false`) carries a target and a reason and
never an expected exit code: the plan turns it into an open question for the orchestrator.

The scout writes calibrations into its scope report; for a check the orchestrator declares
by CLI the machine runs the command itself and writes the calibration. A green whose output
is a zero-work signature ("No tests found", "0 files analyzed") is refused in both routes:
a green that did no work protects nothing (ECO-856 F3, ECO-1281 F1).
"""

import re
import subprocess

from ai_team.store import MachineError

DEFAULT_TIMEOUT_S = 600
DIGEST_LINES = 3
DIGEST_WIDTH = 200

EXIT_FORM = re.compile(r"^exit (\d+)$")
ZERO_WORK = (
    re.compile(r"\bno tests? (?:were |was )?(?:found|executed|ran|run)\b", re.I),
    re.compile(r"\bno test files? (?:were )?found\b", re.I),
    re.compile(r"\b0 (?:files?|tests?|suites?) (?:analy[sz]ed|executed|found|run|ran)\b", re.I),
    re.compile(r"\bno files? (?:were )?analy[sz]ed\b", re.I),
    re.compile(r"\btests:\s+0 total\b", re.I),
    re.compile(r"\bnothing to (?:test|analy[sz]e|check)\b", re.I),
)


def zero_work_signature(text):
    """The zero-work phrase found in `text`, or None when the output shows real work."""
    for pattern in ZERO_WORK:
        match = pattern.search(text or "")
        if match:
            return match.group(0)
    return None


def expected_exit(expect):
    """The N of an `exit N` expectation, or None for any other shape."""
    match = EXIT_FORM.match(expect) if isinstance(expect, str) else None
    return int(match.group(1)) if match else None


def _is_strict_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _non_empty(value):
    return isinstance(value, str) and value.strip() != ""


def validate_check(entry, where):
    """(normalized entry, violations). The entry is normalized to the plan's shape even when
    violations exist, so a caller can report everything at once."""
    violations = []
    if not isinstance(entry, dict):
        return None, ["%s must be an object" % where]
    command = entry.get("command")
    if not _non_empty(command):
        violations.append("%s.command must be a non-empty string" % where)
    calibration = entry.get("calibration")
    if not isinstance(calibration, dict):
        violations.append(
            "%s needs a calibration object -- {executed: true, exit_code, digest, failure_signature | red_reason} "
            "or {executed: false, target, reason}; a free-text `verified` note is not one" % where)
        return None, violations
    executed = calibration.get("executed")
    if executed is True:
        return _validate_executed(entry, calibration, command, where, violations)
    if executed is False:
        return _validate_unrun(entry, calibration, command, where, violations)
    violations.append("%s.calibration.executed must be true or false (got %r)" % (where, executed))
    return None, violations


def _validate_executed(entry, calibration, command, where, violations):
    expect = entry.get("expect")
    expected = expected_exit(expect)
    if expected is None:
        violations.append("%s.expect must be of the form `exit N` (got %r)" % (where, expect))
    exit_code = calibration.get("exit_code")
    if not _is_strict_int(exit_code):
        violations.append("%s.calibration.exit_code must be an integer (got %r)" % (where, exit_code))
    digest = calibration.get("digest")
    if not _non_empty(digest):
        violations.append("%s.calibration.digest must quote the command's output (use \"(no output)\" when silent)" % where)
    else:
        signature = zero_work_signature(digest)
        if signature:
            violations.append("%s.calibration.digest is a zero-work output (%r) -- a green that did no work is never a calibration" % (where, signature))
    normalized = {"command": command, "expect": expect,
                  "calibration": {"executed": True, "exit_code": exit_code, "digest": digest}}
    if expected is not None and _is_strict_int(exit_code):
        if exit_code == expected:
            signature = calibration.get("failure_signature")
            if not _non_empty(signature):
                violations.append("%s is green today (exit %d) -- calibration.failure_signature must say how a known failure of this command shows"
                                  % (where, exit_code))
            normalized["calibration"]["failure_signature"] = signature
        else:
            reason = calibration.get("red_reason")
            if not _non_empty(reason):
                violations.append("%s is red today (exit %d, expected %d) -- calibration.red_reason must say why it fails now and that this phase turns it green"
                                  % (where, exit_code, expected))
            normalized["calibration"]["red_reason"] = reason
    if "tree" in calibration:
        normalized["calibration"]["tree"] = calibration["tree"]
    return normalized, violations


def _validate_unrun(entry, calibration, command, where, violations):
    if entry.get("expect") is not None:
        violations.append("%s has executed: false and still carries expect %r -- a check nobody ran has no expected exit code"
                          % (where, entry.get("expect")))
    target = calibration.get("target")
    reason = calibration.get("reason")
    if not _non_empty(target):
        violations.append("%s.calibration.target must cite where the command is declared (file:line)" % where)
    if not _non_empty(reason):
        violations.append("%s.calibration.reason must say why the check was not run" % where)
    normalized = {"command": command, "calibration": {"executed": False, "target": target, "reason": reason}}
    return normalized, violations


def validate_scope_checks(phases_by_n):
    """Every calibration violation across a scope report's phases; empty means valid."""
    violations = []
    for n in sorted(phases_by_n):
        checks = phases_by_n[n].get("acceptance_checks")
        if checks is None:
            continue
        if not isinstance(checks, list):
            violations.append("phases[n=%d].acceptance_checks must be a list" % n)
            continue
        for i, entry in enumerate(checks):
            _, found = validate_check(entry, "phases[n=%d].acceptance_checks[%d]" % (n, i))
            violations += found
    return violations


def is_calibrated(check):
    calibration = check.get("calibration")
    return isinstance(calibration, dict) and calibration.get("executed") is True


def demotion_question(check, phase_n):
    calibration = check["calibration"]
    return ("not calibrated: `%s` -- %s (%s). Run it yourself before delegating and record it with "
            "`ai-team plan amend --phase %d --reason \"...\" --check \"%s\" --failure \"<how it fails>\"`, or drop it"
            % (check["command"], calibration["reason"], calibration["target"], phase_n, check["command"]))


def state_note(check, phase_n, source):
    """The line `plan generate` prints for a calibrated check -- loud when it is red today."""
    calibration = check["calibration"]
    expected = expected_exit(check.get("expect"))
    if calibration["exit_code"] != expected:
        why = calibration.get("red_reason")
        return "phase %d: `%s` is red today (exit %d: %s) -- %s" % (
            phase_n, check["command"], calibration["exit_code"], calibration["digest"],
            "%s: %s" % (source, why) if why else "no reason recorded (scope skipped)")
    if calibration.get("failure_signature") is None:
        return "phase %d: `%s` is green today (exit %d) -- not shown able to fail (scope skipped)" % (
            phase_n, check["command"], calibration["exit_code"])
    return None


def _digest(output):
    lines = [line.strip()[:DIGEST_WIDTH] for line in output.splitlines() if line.strip()]
    return "\n".join(lines[-DIGEST_LINES:]) if lines else "(no output)"


def _tree(cwd):
    try:
        head = subprocess.run(["git", "-C", cwd, "rev-parse", "--short=12", "HEAD"], capture_output=True, text=True, check=False)
        if head.returncode != 0:
            return "unknown"
        status = subprocess.run(["git", "-C", cwd, "status", "--porcelain"], capture_output=True, text=True, check=False)
        dirty = "+dirty" if status.stdout.strip() else ""
        return head.stdout.strip() + dirty
    except OSError:
        return "unknown"


def calibrate_by_running(command, failure, cwd, timeout_s=DEFAULT_TIMEOUT_S, expect="exit 0"):
    """Run `command` on the current tree and write its calibration. `failure` is the
    orchestrator's `--failure` text (how the check fails: a known failure's signature when
    it is green today, why it is red today otherwise); None records that nothing was shown."""
    tree = _tree(cwd)  # before the run: a check may write caches or build output
    try:
        completed = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout_s, check=False)
    except subprocess.TimeoutExpired:
        raise MachineError("check `%s` timed out after %ds -- calibrate a narrower check or raise --check-timeout" % (command, timeout_s))
    output = (completed.stdout or "") + (completed.stderr or "")
    expected = expected_exit(expect)
    if completed.returncode == expected:
        signature = zero_work_signature(output)
        if signature:
            raise MachineError("check `%s` is a zero-work green (%r) -- it did nothing on this tree and is never an acceptance check"
                               % (command, signature))
    calibration = {"executed": True, "exit_code": completed.returncode, "digest": _digest(output), "tree": tree}
    if completed.returncode == expected:
        calibration["failure_signature"] = failure
    else:
        calibration["red_reason"] = failure
    return {"command": command, "expect": expect, "calibration": calibration}


def check_line(check):
    """One Markdown bullet for a plan or phase file."""
    calibration = check.get("calibration")
    if not isinstance(calibration, dict):
        return "`%s` — %s · uncalibrated (pre-schema)" % (check["command"], check.get("expect", "?"))
    if calibration.get("executed") is not True:
        return "`%s` — not calibrated: %s" % (check["command"], calibration.get("reason", "?"))
    expected = expected_exit(check.get("expect"))
    exit_code = calibration["exit_code"]
    digest = " / ".join(str(calibration["digest"]).splitlines())
    if exit_code == expected:
        how = calibration.get("failure_signature")
        return "`%s` — %s · green today (exit %d: «%s») · fails as: %s" % (
            check["command"], check["expect"], exit_code, digest, how or "not shown (scope skipped)")
    why = calibration.get("red_reason")
    return "`%s` — %s · red today (exit %d: «%s») · because: %s" % (
        check["command"], check["expect"], exit_code, digest, why or "no reason recorded (scope skipped)")
