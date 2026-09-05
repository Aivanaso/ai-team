"""Review Receipt validation -- the structural half inherited from check-receipt.py.

Structure only: nothing is re-run, the report's prose is never read, and a cited file is
opened for nothing beyond a containment + existence check under project_root. A receipt is
either a FULL reviewer receipt (the default) or a SECURITY FRAGMENT (`kind:
"security-fragment"`); the absence of lenses.correctness is never the discriminator.

Removed from the inherited validator, because the machine now owns those decisions:
`overrides`, `findings_addressed`, `exposure` (rulings live in the task JSON; inline
closure and stored-data exposure no longer exist) and the whole ledger half.

Exit codes of `ai-team receipt check`: 0 valid (INFO lines allowed), 1 VIOLATION lines on
stdout, 2 one ERROR line on stderr (validation could not run at all).
"""

import os
import unicodedata

from ai_team.fenced import load_json_block

SEVERITIES = ("CRITICAL", "MAJOR", "MINOR")
CONFIDENCES = ("high", "medium", "low")
EVIDENCE_KINDS = ("executed", "read")
VERDICTS = ("review-clear", "review-blocked")
KINDS = ("security-fragment",)


def _is_strict_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def check_containment(project_root, file_field):
    """(True, None) when file_field is a regular file CONTAINED under project_root."""
    if os.path.isabs(file_field):
        return False, "absolute paths are not permitted as citations"
    try:
        real_root = os.path.realpath(project_root)
        real_joined = os.path.realpath(os.path.join(project_root, file_field))
    except (ValueError, OSError) as exc:
        return False, "unusable path string (%s)" % type(exc).__name__
    try:
        common = os.path.commonpath([real_root, real_joined])
    except ValueError:
        return False, "does not resolve under project_root"
    if common != real_root:
        return False, "resolves outside project_root (traversal or symlink escape)"
    if not os.path.isfile(real_joined):
        return False, "does not resolve to a regular file on disk"
    return True, None


def _check_finding(where, finding, project_root, violations, skip_containment):
    if not isinstance(finding, dict):
        violations.append("%s must be an object" % where)
        return None, None
    fid = finding.get("id")
    if not isinstance(fid, str) or not fid:
        violations.append("%s.id must be a non-empty string" % where)
        fid = None
    severity = finding.get("severity")
    if severity not in SEVERITIES:
        violations.append("%s.severity must be one of %s (got %r)" % (where, list(SEVERITIES), severity))
    confidence = finding.get("confidence")
    if confidence not in CONFIDENCES:
        violations.append("%s.confidence must be one of %s (got %r)" % (where, list(CONFIDENCES), confidence))
    evidence = finding.get("evidence")
    if evidence not in EVIDENCE_KINDS:
        violations.append("%s.evidence must be one of %s (got %r)" % (where, list(EVIDENCE_KINDS), evidence))
    file_field = finding.get("file")
    if not isinstance(file_field, str) or not file_field:
        violations.append("%s.file must be a non-empty string" % where)
    elif os.path.isabs(file_field):
        # A pure string check: runs even under a degenerate root.
        violations.append("%s.file %r: absolute paths are not permitted as citations" % (where, file_field))
    elif not skip_containment:
        ok, reason = check_containment(project_root, file_field)
        if not ok:
            violations.append("%s.file %r: %s" % (where, file_field, reason))
    line = finding.get("line")
    if not _is_strict_int(line) or line < 1:
        violations.append("%s.line must be an integer >= 1 (got %r)" % (where, line))
    claim = finding.get("claim")
    if not isinstance(claim, str) or not claim.strip():
        violations.append("%s.claim must be a non-empty string" % where)
    trigger = finding.get("trigger")
    if severity in ("MAJOR", "CRITICAL") and evidence == "read":
        if not isinstance(trigger, str) or not trigger.strip():
            violations.append(
                "%s.trigger must be a non-empty string when severity is MAJOR/CRITICAL and "
                "evidence is read" % where
            )
    return fid, severity


def _check_lens(lens_name, lenses, project_root, violations, skip_containment):
    ids = []
    any_critical = False
    lens = lenses.get(lens_name)
    if lens is None:
        return ids, any_critical
    if not isinstance(lens, dict):
        violations.append("lenses.%s must be an object" % lens_name)
        return ids, any_critical
    status = lens.get("status")
    if status not in ("pass", "findings"):
        violations.append("lenses.%s.status must be 'pass' or 'findings' (got %r)" % (lens_name, status))
    findings = lens.get("findings", [])
    if not isinstance(findings, list):
        violations.append("lenses.%s.findings must be a list" % lens_name)
        findings = []
    for i, finding in enumerate(findings):
        where = "lenses.%s.findings[%d]" % (lens_name, i)
        fid, severity = _check_finding(where, finding, project_root, violations, skip_containment)
        if fid:
            ids.append(fid)
        if severity == "CRITICAL":
            any_critical = True
    if status == "pass" and findings:
        violations.append("lenses.%s.status is 'pass' but findings is non-empty (%d entries)" % (lens_name, len(findings)))
    if status == "findings" and not findings:
        violations.append("lenses.%s.status is 'findings' but findings is empty" % lens_name)
    return ids, any_critical


def _check_duplicate_ids(ids, violations):
    seen = set()
    duplicates = set()
    for fid in ids:
        key = unicodedata.normalize("NFC", fid)
        if key in seen:
            duplicates.add(fid)
        seen.add(key)
    for dup in sorted(duplicates):
        violations.append("duplicate finding id (after Unicode normalization): %r" % dup)


def _check_verdict_history(data, violations):
    history = data.get("verdict_history")
    if history is None:
        return
    if not isinstance(history, list) or not history:
        violations.append("verdict_history must be a non-empty list when present")
        return
    for i, entry in enumerate(history):
        where = "verdict_history[%d]" % i
        if not isinstance(entry, dict):
            violations.append("%s must be an object" % where)
            continue
        if entry.get("pass") not in ("full", "delta"):
            violations.append("%s.pass must be 'full' or 'delta' (got %r)" % (where, entry.get("pass")))
        report = entry.get("report")
        if not isinstance(report, str) or not report.strip():
            violations.append("%s.report must be a non-empty string" % where)
        if entry.get("verdict") not in VERDICTS:
            violations.append("%s.verdict must be one of %s (got %r)" % (where, list(VERDICTS), entry.get("verdict")))
        note = entry.get("note")
        if not isinstance(note, str) or not note.strip():
            violations.append("%s.note must be a non-empty string" % where)
    last = history[-1]
    if not isinstance(last, dict) or last.get("verdict") != data.get("verdict"):
        violations.append("verdict_history's last entry verdict must match the top-level verdict")


def validate_receipt(data, project_root):
    """Return (violations, infos) for an already-parsed receipt object."""
    violations = []
    infos = []

    real_root = os.path.realpath(project_root)
    degenerate_root = real_root == os.path.abspath(os.sep) or not os.path.isdir(real_root)
    if degenerate_root:
        violations.append(
            "project_root %r resolves to %r -- must be an existing directory other than the "
            "filesystem root (containment against the root is a tautology)" % (project_root, real_root)
        )

    kind = data.get("kind")
    if kind is not None and kind not in KINDS:
        violations.append("kind, when present, must be one of %s (got %r)" % (list(KINDS), kind))
    is_fragment = kind == "security-fragment"

    tier = data.get("tier")
    if not _is_strict_int(tier) or tier not in (0, 1, 2):
        violations.append("tier must be an int in {0, 1, 2} (got %r)" % (tier,))
    tier_reason = data.get("tier_reason")
    if not isinstance(tier_reason, str) or not tier_reason.strip():
        violations.append("tier_reason must be a non-empty string")

    lenses = data.get("lenses")
    if not isinstance(lenses, dict):
        violations.append("lenses must be an object")
        lenses = {}
    correctness_declared = "correctness" in lenses
    correctness_valid = correctness_declared and lenses.get("correctness") is not None
    if correctness_declared and lenses.get("correctness") is None:
        violations.append("lenses.correctness must be an object, not null")
    security_declared = "security" in lenses
    security_valid = security_declared and lenses.get("security") is not None
    if security_declared and lenses.get("security") is None:
        violations.append("lenses.security must be an object, not null")

    if is_fragment:
        if correctness_declared:
            violations.append("a security-fragment (kind: security-fragment) must not declare lenses.correctness")
        if not security_valid:
            violations.append("a security-fragment (kind: security-fragment) must declare lenses.security")
    elif not correctness_valid:
        violations.append('lenses.correctness is required unless the top-level kind: "security-fragment" is declared')

    correctness_ids, critical_correctness = (
        _check_lens("correctness", lenses, project_root, violations, degenerate_root)
        if correctness_valid else ([], False)
    )
    security_ids, critical_security = (
        _check_lens("security", lenses, project_root, violations, degenerate_root)
        if security_valid else ([], False)
    )
    _check_duplicate_ids(correctness_ids + security_ids, violations)

    verdict = data.get("verdict")
    if is_fragment:
        if verdict is not None:
            if verdict not in VERDICTS:
                violations.append("verdict, when present on a security fragment, must be one of %s (got %r)" % (list(VERDICTS), verdict))
            elif critical_security and verdict != "review-blocked":
                violations.append("verdict must be 'review-blocked' -- this security fragment has a CRITICAL finding")
            elif not critical_security and verdict == "review-blocked":
                violations.append("verdict must not be 'review-blocked' -- this security fragment has no CRITICAL finding")
    else:
        if verdict not in VERDICTS:
            violations.append("verdict must be one of %s (got %r)" % (list(VERDICTS), verdict))
        elif critical_correctness:
            if verdict != "review-blocked":
                violations.append("verdict must be 'review-blocked' -- lenses.correctness has a CRITICAL finding")
        elif verdict != "review-clear":
            violations.append("verdict must be 'review-clear' -- no CRITICAL finding in lenses.correctness")
        if critical_security and not critical_correctness:
            infos.append(
                "CRITICAL finding(s) present only in lenses.security -- this verdict reflects "
                "lenses.correctness alone; the machine combines tier-2 verdicts at commit-check"
            )

    verification = data.get("verification")
    if is_fragment:
        if verification is not None and not isinstance(verification, list):
            violations.append("verification must be a list when present")
        if "verification_omitted_reason" in data:
            violations.append(
                "verification_omitted_reason must be absent on a security fragment -- "
                "verification is optional there and needs no justification"
            )
    else:
        omitted_reason = data.get("verification_omitted_reason")
        if not isinstance(verification, list):
            violations.append("verification must be a list on a full receipt")
        elif not verification:
            if not isinstance(omitted_reason, str) or not omitted_reason.strip():
                violations.append(
                    "verification is empty on a full receipt -- a receipt that re-ran nothing "
                    "must state why in verification_omitted_reason (non-empty string)"
                )
        elif omitted_reason is not None:
            violations.append("verification_omitted_reason must be absent when verification is non-empty")
    if isinstance(verification, list):
        for i, entry in enumerate(verification):
            where = "verification[%d]" % i
            if not isinstance(entry, dict):
                violations.append("%s must be an object" % where)
                continue
            command = entry.get("command")
            if not isinstance(command, str) or not command.strip():
                violations.append("%s.command must be a non-empty string" % where)
            if not _is_strict_int(entry.get("exit_code")):
                violations.append("%s.exit_code must be an integer" % where)
            if entry.get("outcome") not in ("pass", "fail"):
                violations.append("%s.outcome must be 'pass' or 'fail'" % where)

    not_reverified = data.get("not_reverified")
    if not_reverified is not None:
        if not isinstance(not_reverified, list):
            violations.append("not_reverified must be a list when present")
        else:
            for i, entry in enumerate(not_reverified):
                if not isinstance(entry, str) or not entry.strip():
                    violations.append("not_reverified[%d] must be a non-empty string" % i)

    _check_verdict_history(data, violations)
    return violations, infos


def findings_of(data):
    """Flatten a validated receipt's findings: [{id, severity, lens, file, line, claim, trigger}]."""
    out = []
    lenses = data.get("lenses") or {}
    for lens_name in ("correctness", "security"):
        lens = lenses.get(lens_name)
        if not isinstance(lens, dict):
            continue
        for finding in lens.get("findings") or []:
            if isinstance(finding, dict):
                out.append({
                    "id": finding.get("id"),
                    "severity": finding.get("severity"),
                    "lens": lens_name,
                    "file": finding.get("file"),
                    "line": finding.get("line"),
                    "claim": finding.get("claim"),
                    "trigger": finding.get("trigger"),
                    "evidence": finding.get("evidence"),
                })
    return out


def derived_verdict(data):
    """A full receipt's own verdict; a fragment's is derived from its CRITICAL findings."""
    if data.get("kind") == "security-fragment":
        critical = any(f["severity"] == "CRITICAL" for f in findings_of(data))
        return "review-blocked" if critical else "review-clear"
    return data.get("verdict")


def validate_report(path, project_root):
    """Validate the receipt block of a report on disk.

    Returns (exit_code, stdout_lines, stderr_lines, data). data is the parsed object on
    exit 0, else None.
    """
    data, error = load_json_block(path)
    if error is not None:
        kind, message = error
        if kind in ("block-error", "json-error"):
            return 1, ["VIOLATION %s: %s" % (path, message)], [], None
        return 2, [], ["ERROR %s: %s" % (path, message)], None
    if not isinstance(data, dict):
        return 2, [], ["ERROR %s: top-level JSON value must be an object (got %s)" % (path, type(data).__name__)], None
    try:
        violations, infos = validate_receipt(data, project_root)
    except Exception as exc:  # noqa: BLE001 -- fail closed, never a traceback
        return 2, [], ["ERROR %s: %s: %s" % (path, type(exc).__name__, exc)], None
    if violations:
        return 1, ["VIOLATION %s: %s" % (path, v) for v in violations], [], None
    return 0, ["INFO %s: %s" % (path, i) for i in infos], [], data
