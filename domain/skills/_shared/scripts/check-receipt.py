#!/usr/bin/env python3
"""check-receipt.py -- mechanical structural validator for Review Receipt and
Brief File Cost Ledger JSON sidecars (orchestrator-protocol.md "Citation audit"
and "Brief File structural check").

This tool checks STRUCTURE only: it never re-runs any acceptance/build/gate
command, never reads the paired .md report, and never opens a cited file
beyond a plain containment + existence check under project_root. Validating
structure, not content, is the whole point -- prose was never a safe parse
target.

Modes:
  receipt <file.json> [project_root]   validate a Review Receipt JSON sidecar
  ledger  <file.json>                  validate a Brief File ledger+close sidecar

A receipt sidecar is either a FULL reviewer receipt (the default) or a
declared SECURITY FRAGMENT (top-level "kind": "security-fragment"). Absence of
lenses.correctness is never itself the discriminator -- only the explicit
"kind" field is. A full receipt REQUIRES lenses.correctness and verdict; a
fragment REQUIRES lenses.security and forbids lenses.correctness.

Exit codes:
  0  valid
  1  the file parsed as JSON but is structurally invalid -- one or more
     "VIOLATION <path>: <what>" lines are printed to stdout
  2  anything that prevented validation from running at all (missing/unreadable
     file, invalid UTF-8, pathological input, a top-level JSON value that is
     not an object, or any other unexpected error) -- exactly one
     "ERROR <path>: <what>" line is printed to stderr, never a traceback

Stdout channels: "VIOLATION <path>: <what>" (exit 1) and, on exit 0 only,
zero or more "INFO <path>: <what>" lines -- advisory notes (e.g. CRITICAL
findings present only in lenses.security, whose combination into the final
tier-2 verdict is the orchestrator's job). INFO never changes the exit code.

verification: a full receipt REQUIRES a non-empty verification[] list, OR an
empty list accompanied by verification_omitted_reason (non-empty string) --
the two contract-prescribed cases being "no candidate changes to review" and
"every declared check is unrunnable in this environment". A fragment's
verification is optional and verification_omitted_reason must be ABSENT on it.

"kind" semantics: absent or explicit null = full reviewer receipt; the string
"security-fragment" = fragment; ANY other value (other strings, wrong case,
numbers, arrays) is a VIOLATION -- an unrecognized kind is never silently
treated as a full receipt.

project_root: must not resolve to the filesystem root -- containment against
"/" is a tautology, so a degenerate project_root is itself a VIOLATION.
"""

import argparse
import json
import os
import sys
import unicodedata

SEVERITIES = ("CRITICAL", "MAJOR", "MINOR")
CONFIDENCES = ("high", "medium", "low")
EVIDENCE_KINDS = ("executed", "read")
VERDICTS = ("review-clear", "review-blocked")
KINDS = ("security-fragment",)

WORK_UNIT_COMMITS_AGENT = "work-unit-commits"


def _is_strict_int(value):
    """True for a real int, excluding bool (bool is a subclass of int)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _check_containment(project_root, file_field):
    """Verify file_field is a real, on-disk file CONTAINED inside project_root.

    Containment = realpath(project_root) is a commonpath ancestor of
    realpath(join(project_root, file_field)) AND the resolved path is a
    regular file (os.path.isfile). An absolute file_field is rejected before
    any resolution is attempted -- os.path.join silently drops project_root
    when the second argument is absolute, so this must be checked first.

    Returns (True, None) or (False, "<reason>").
    """
    if os.path.isabs(file_field):
        return False, "absolute paths are not permitted as citations"

    try:
        real_root = os.path.realpath(project_root)
        real_joined = os.path.realpath(os.path.join(project_root, file_field))
    except (ValueError, OSError) as exc:
        # e.g. embedded NUL byte, path too long -- a DATA defect in the citation,
        # reported as a VIOLATION, never escalated to the exit-2 catch-all.
        return False, "unusable path string (%s)" % type(exc).__name__

    try:
        common = os.path.commonpath([real_root, real_joined])
    except ValueError:
        # Different drive/anchor -- cannot share a common path at all.
        return False, "does not resolve under project_root"

    if common != real_root:
        return False, "resolves outside project_root (traversal or symlink escape)"

    if not os.path.isfile(real_joined):
        return False, "does not resolve to a regular file on disk"

    return True, None


def _check_finding(where, finding, project_root, violations):
    """Validate one finding object. Returns (id, severity) -- either may be None."""
    if not isinstance(finding, dict):
        violations.append("%s must be an object" % where)
        return None, None

    fid = finding.get("id")
    if not isinstance(fid, str) or not fid:
        violations.append("%s.id must be a non-empty string" % where)
        fid = None

    severity = finding.get("severity")
    if severity not in SEVERITIES:
        violations.append(
            "%s.severity must be one of %s (got %r)" % (where, list(SEVERITIES), severity)
        )

    confidence = finding.get("confidence")
    if confidence not in CONFIDENCES:
        violations.append(
            "%s.confidence must be one of %s (got %r)" % (where, list(CONFIDENCES), confidence)
        )

    evidence = finding.get("evidence")
    if evidence not in EVIDENCE_KINDS:
        violations.append(
            "%s.evidence must be one of %s (got %r)" % (where, list(EVIDENCE_KINDS), evidence)
        )

    file_field = finding.get("file")
    if not isinstance(file_field, str) or not file_field:
        violations.append("%s.file must be a non-empty string" % where)
    else:
        ok, reason = _check_containment(project_root, file_field)
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
                "%s.trigger must be a non-empty string when severity is MAJOR/CRITICAL "
                "and evidence is read" % where
            )

    return fid, severity


def _check_lens(lens_name, lenses, project_root, violations):
    """Walk one lens ('correctness' or 'security'). Returns (ids, any_critical)."""
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
        violations.append(
            "lenses.%s.status must be 'pass' or 'findings' (got %r)" % (lens_name, status)
        )

    findings = lens.get("findings", [])
    if not isinstance(findings, list):
        violations.append("lenses.%s.findings must be a list" % lens_name)
        findings = []

    for i, finding in enumerate(findings):
        where = "lenses.%s.findings[%d]" % (lens_name, i)
        fid, severity = _check_finding(where, finding, project_root, violations)
        if fid:
            ids.append(fid)
        if severity == "CRITICAL":
            any_critical = True

    if status == "pass" and len(findings) > 0:
        violations.append(
            "lenses.%s.status is 'pass' but findings is non-empty (%d entries)"
            % (lens_name, len(findings))
        )
    if status == "findings" and len(findings) == 0:
        violations.append("lenses.%s.status is 'findings' but findings is empty" % lens_name)

    return ids, any_critical


def _check_duplicate_ids(correctness_ids, security_ids, violations):
    """Duplicate-id check normalized with NFC only, so ids that differ solely in
    Unicode composition (NFC vs NFD) are caught. Case-folding is deliberately
    NOT applied: ids are case-sensitive by contract (F-1 vs f-1 are distinct
    strings), and casefold would false-collide legitimately distinct ids
    (e.g. F-ß vs F-ss)."""
    seen = {}
    duplicates = set()
    for fid in correctness_ids + security_ids:
        key = unicodedata.normalize("NFC", fid)
        if key in seen:
            duplicates.add(fid)
        seen[key] = fid
    for dup in sorted(duplicates):
        violations.append("duplicate finding id (after Unicode normalization): %r" % dup)


def _check_overrides(data, violations):
    overrides = data.get("overrides")
    if overrides is None:
        return
    if not isinstance(overrides, list):
        violations.append("overrides must be a list when present")
        return
    for i, entry in enumerate(overrides):
        where = "overrides[%d]" % i
        if not isinstance(entry, dict):
            violations.append("%s must be an object" % where)
            continue
        has_single = "finding_id" in entry
        has_bulk = "finding_ids" in entry
        if has_single == has_bulk:
            violations.append("%s must have exactly one of finding_id or finding_ids" % where)
        justification = entry.get("justification")
        if not isinstance(justification, str) or not justification.strip():
            violations.append("%s.justification must be a non-empty string" % where)


def _check_findings_addressed(data, violations):
    entries = data.get("findings_addressed")
    if entries is None:
        return
    if not isinstance(entries, list):
        violations.append("findings_addressed must be a list when present")
        return
    for i, entry in enumerate(entries):
        where = "findings_addressed[%d]" % i
        if not isinstance(entry, dict):
            violations.append("%s must be an object" % where)
            continue
        if not entry.get("finding_id"):
            violations.append("%s.finding_id is required" % where)
        files = entry.get("files")
        if not isinstance(files, list) or len(files) == 0:
            violations.append("%s.files must be a non-empty list" % where)
        if not entry.get("fix_evidence"):
            violations.append("%s.fix_evidence is required" % where)
        if not entry.get("gate_results"):
            violations.append("%s.gate_results is required" % where)


def _check_verdict_history(data, violations):
    """Validate every verdict_history entry's shape (not just the last one),
    and require the last entry's verdict to mirror the top-level verdict."""
    verdict_history = data.get("verdict_history")
    if verdict_history is None:
        return
    if not isinstance(verdict_history, list) or len(verdict_history) == 0:
        violations.append("verdict_history must be a non-empty list when present")
        return

    top_verdict = data.get("verdict")
    for i, entry in enumerate(verdict_history):
        where = "verdict_history[%d]" % i
        if not isinstance(entry, dict):
            violations.append("%s must be an object" % where)
            continue
        if entry.get("pass") not in ("full", "delta"):
            violations.append("%s.pass must be 'full' or 'delta' (got %r)" % (where, entry.get("pass")))
        report = entry.get("report")
        if not isinstance(report, str) or not report.strip():
            violations.append("%s.report must be a non-empty string" % where)
        verdict = entry.get("verdict")
        if verdict not in VERDICTS:
            violations.append("%s.verdict must be one of %s (got %r)" % (where, list(VERDICTS), verdict))
        note = entry.get("note")
        if not isinstance(note, str) or not note.strip():
            violations.append("%s.note must be a non-empty string" % where)

    last = verdict_history[-1]
    if not isinstance(last, dict) or last.get("verdict") != top_verdict:
        violations.append("verdict_history's last entry verdict must match the top-level verdict")


def validate_receipt(data, project_root):
    violations = []
    infos = []

    real_root = os.path.realpath(project_root)
    if real_root == os.path.abspath(os.sep) or not os.path.isdir(real_root):
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
    else:
        if not correctness_valid:
            violations.append(
                "lenses.correctness is required unless the top-level kind: \"security-fragment\" is declared"
            )

    correctness_ids, any_critical_correctness = (
        _check_lens("correctness", lenses, project_root, violations) if correctness_valid else ([], False)
    )
    security_ids, any_critical_security = (
        _check_lens("security", lenses, project_root, violations) if security_valid else ([], False)
    )

    _check_duplicate_ids(correctness_ids, security_ids, violations)

    verdict = data.get("verdict")

    if is_fragment:
        if verdict is not None:
            if verdict not in VERDICTS:
                violations.append(
                    "verdict, when present on a security fragment, must be one of %s (got %r)"
                    % (list(VERDICTS), verdict)
                )
            elif any_critical_security and verdict != "review-blocked":
                violations.append(
                    "verdict must be 'review-blocked' -- this security fragment has a CRITICAL finding"
                )
            elif not any_critical_security and verdict == "review-blocked":
                violations.append(
                    "verdict must not be 'review-blocked' -- this security fragment has no CRITICAL finding"
                )
    else:
        if verdict not in VERDICTS:
            violations.append("verdict must be one of %s (got %r)" % (list(VERDICTS), verdict))
        elif any_critical_correctness:
            if verdict != "review-blocked":
                violations.append(
                    "verdict must be 'review-blocked' -- lenses.correctness has a CRITICAL finding"
                )
        elif verdict != "review-clear":
            violations.append(
                "verdict must be 'review-clear' -- no CRITICAL finding in lenses.correctness"
            )
        if any_critical_security and not any_critical_correctness:
            infos.append(
                "CRITICAL finding(s) present only in lenses.security -- this verdict reflects "
                "lenses.correctness alone; the orchestrator combines tier-2 verdicts"
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
        # A full receipt with no re-run evidence is the zero-work class: a
        # zero-finding receipt that verified nothing must not read as a clean
        # pass. Two contract-prescribed shapes legitimately carry an empty list
        # (no candidate changes to review; every declared check unrunnable in
        # this environment -- organic-reviewer Decision Gates), so an empty
        # verification is accepted ONLY when the receipt says why, in
        # verification_omitted_reason (non-empty string).
        omitted_reason = data.get("verification_omitted_reason")
        if not isinstance(verification, list):
            violations.append("verification must be a list on a full receipt")
        elif len(verification) == 0:
            if not isinstance(omitted_reason, str) or not omitted_reason.strip():
                violations.append(
                    "verification is empty on a full receipt -- a receipt that re-ran nothing "
                    "must state why in verification_omitted_reason (non-empty string)"
                )
        elif omitted_reason is not None:
            violations.append(
                "verification_omitted_reason must be absent when verification is non-empty"
            )
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
    _check_overrides(data, violations)
    _check_findings_addressed(data, violations)

    return violations, infos


def validate_ledger(data):
    violations = []

    ledger = data.get("ledger")
    if not isinstance(ledger, list):
        violations.append("ledger must be a list")
        ledger = []

    token_sum = 0
    has_work_unit_commits = False
    seen_n = set()
    for i, row in enumerate(ledger):
        where = "ledger[%d]" % i
        if not isinstance(row, dict):
            violations.append("%s must be an object" % where)
            continue

        n = row.get("n")
        if not _is_strict_int(n):
            violations.append("%s.n must be an integer (got %r)" % (where, n))
        elif n in seen_n:
            violations.append("%s.n duplicates a previous row's n (%r)" % (where, n))
        else:
            seen_n.add(n)

        for field in ("tokens", "tool_uses", "duration_s"):
            value = row.get(field)
            if not _is_strict_int(value):
                violations.append("%s.%s must be an integer (got %r)" % (where, field, value))
            elif value < 0:
                violations.append("%s.%s must be >= 0 (got %r)" % (where, field, value))

        for field in ("agent", "model", "outcome"):
            value = row.get(field)
            if not isinstance(value, str) or not value:
                violations.append("%s.%s must be a non-empty string" % (where, field))

        tokens = row.get("tokens")
        if _is_strict_int(tokens):
            token_sum += tokens

        agent = row.get("agent")
        if agent == WORK_UNIT_COMMITS_AGENT:
            has_work_unit_commits = True

    close = data.get("close")
    if close is None:
        violations.append(
            "close is required -- the gate's only prescribed invocation is immediately "
            "before the status:done flip, where close is always mandatory"
        )
    elif not isinstance(close, dict):
        violations.append("close must be an object")
    else:
        delegations = close.get("delegations")
        if not _is_strict_int(delegations) or delegations < 0:
            violations.append("close.delegations must be a non-negative integer (got %r)" % (delegations,))
        elif delegations != len(ledger):
            violations.append(
                "close.delegations (%r) must equal the ledger row count (%d)"
                % (delegations, len(ledger))
            )

        subagent_tokens = close.get("subagent_tokens")
        if not _is_strict_int(subagent_tokens) or subagent_tokens < 0:
            violations.append(
                "close.subagent_tokens must be a non-negative integer (got %r)" % (subagent_tokens,)
            )
        elif subagent_tokens != token_sum:
            violations.append(
                "close.subagent_tokens (%r) must equal the sum of the ledger's tokens "
                "column (%d)" % (subagent_tokens, token_sum)
            )

        commits = close.get("commits")
        if not isinstance(commits, list):
            violations.append("close.commits must be a list")
        else:
            for i, sha in enumerate(commits):
                if not isinstance(sha, str) or not sha.strip():
                    violations.append("close.commits[%d] must be a non-empty string" % i)

        re_briefs = close.get("re_briefs")
        if not _is_strict_int(re_briefs) or re_briefs < 0:
            violations.append("close.re_briefs must be a non-negative integer (got %r)" % (re_briefs,))

        if not has_work_unit_commits:
            violations.append(
                "close is present but no ledger row's agent is exactly %r"
                % (WORK_UNIT_COMMITS_AGENT,)
            )

    return violations, []


def _read_and_parse(path):
    """Read + JSON-parse `path`. Returns (data, None) on success, or
    (None, (kind, message)) on failure:

    kind == "json-error": the file opened and decoded, but is not valid JSON
                          syntax -- caller prints a VIOLATION line, exit 1.
    kind == "error":      anything else that prevented validation -- caller
                          prints a single ERROR line to stderr, exit 2. Never
                          a raw traceback, regardless of the underlying cause
                          (missing file, unreadable, invalid UTF-8,
                          pathologically nested input, top-level not an
                          object, or any other unexpected failure).
    """
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
        text = raw.decode("utf-8")
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, ("json-error", "not valid JSON: %s" % exc)
    except Exception as exc:  # noqa: BLE001 -- deliberate: fail-closed, never a traceback
        return None, ("error", "%s: %s" % (type(exc).__name__, exc))

    if not isinstance(data, dict):
        return None, ("error", "top-level JSON value must be an object (got %s)" % type(data).__name__)

    return data, None


def main():
    parser = argparse.ArgumentParser(
        prog="check-receipt.py",
        description=(
            "Structural validator for the Review Receipt and Brief File ledger JSON "
            "sidecars. Modes: receipt <file.json> [project_root] | ledger <file.json>."
        ),
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    receipt_parser = subparsers.add_parser("receipt", help="validate a Review Receipt sidecar")
    receipt_parser.add_argument("file", help="path to the receipt .json sidecar")
    receipt_parser.add_argument(
        "project_root",
        nargs="?",
        default=".",
        help="repo root findings' file citations resolve against (default: .)",
    )

    ledger_parser = subparsers.add_parser("ledger", help="validate a Brief File ledger sidecar")
    ledger_parser.add_argument("file", help="path to the ledger .json sidecar")

    args = parser.parse_args()

    data, error = _read_and_parse(args.file)
    if error is not None:
        kind, message = error
        if kind == "json-error":
            print("VIOLATION %s: %s" % (args.file, message))
            sys.exit(1)
        sys.stderr.write("ERROR %s: %s\n" % (args.file, message))
        sys.exit(2)

    try:
        if args.mode == "receipt":
            violations, infos = validate_receipt(data, args.project_root)
        else:
            violations, infos = validate_ledger(data)
    except Exception as exc:  # noqa: BLE001 -- fail-closed: never a traceback
        sys.stderr.write("ERROR %s: %s: %s\n" % (args.file, type(exc).__name__, exc))
        sys.exit(2)

    # INFO lines are advisory and belong to exit-0 runs only (docstring contract);
    # on a violating receipt the VIOLATION lines are the whole story.
    if violations:
        for violation in violations:
            print("VIOLATION %s: %s" % (args.file, violation))
    else:
        for info in infos:
            print("INFO %s: %s" % (args.file, info))

    sys.exit(1 if violations else 0)


if __name__ == "__main__":
    main()
