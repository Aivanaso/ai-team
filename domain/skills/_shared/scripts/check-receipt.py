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
  ledger  <file.json> [project_root]   validate a Brief File ledger+close sidecar

ledger mode's project_root defaults to "." (repo root, matching receipt mode's own
default) and is used only to resolve close.inline_closures[] entries, when present
(see below) -- a legacy ledger sidecar with no inline_closures field validates
identically whether or not project_root is passed, PROVIDED the root resolves to a real
directory other than '/': the degenerate-root rule applies in ledger mode exactly as in
receipt mode, inline_closures present or not.

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
"/" is a tautology, so a degenerate project_root is itself a VIOLATION. This
rule applies identically in ledger mode, against ledger mode's own
project_root argument. In receipt mode, a degenerate project_root ALSO
short-circuits the on-disk resolution+existence half of every per-finding
file-containment probe (lenses.*.findings[].file) -- mirroring ledger mode's
own close.inline_closures short-circuit below -- so a degenerate root can
never be used as an unbounded on-disk existence oracle (does this
absolute/traversal path exist anywhere on the filesystem?) via a finding's
file citation. The pure-string os.path.isabs rejection on that same field is
NOT part of the skipped probe -- it touches no filesystem, so it keeps
running even under a degenerate root (REV F-5): an absolute citation under
project_root "/" still produces its own violation alongside the
degenerate-root one (2 total). Every other per-finding shape check (id,
severity, confidence, evidence, line, claim, trigger) and every receipt-level
shape check (kind, lenses, duplicate ids, overrides, findings_addressed,
verdict_history) still runs under a degenerate root, exactly as before --
only the on-disk resolution+existence walk is skipped.

findings_addressed[].finding_id cross-check (F-7): UNCONDITIONAL for every
receipt that declares findings_addressed (full, delta, and fragment alike).
An entry's finding_id must be a non-empty string -- a missing, null, empty,
blank, or non-string value (e.g. a JSON number) is "finding_id must be a
non-empty string" and never reaches the cross-check below (SEC F-1: this
single predicate replaces what used to be a separate truthy-only "is
required" check, which a truthy non-string id like 42 could pass while also
skipping the cross-check entirely). A finding_id that IS a non-empty string,
after Unicode NFC normalization, must match the NFC-normalized id of some
finding in lenses.correctness.findings[] OR lenses.security.findings[] of the
SAME receipt document -- else "finding_id %r not found in
lenses.*.findings[].id". "Not found" is emitted ONLY when the id is absent
entirely from both lenses -- an id that IS present but whose finding failed
its own severity-enum check is never confused with an absent id (REV F-4:
known_findings membership, not a None-valued lookup, is the discriminator). A
finding_id that DOES resolve but names a CRITICAL finding is also a
VIOLATION -- "finding_id %r names a CRITICAL finding -- inline closure is not
permitted" -- CRITICAL findings are never eligible for the mechanical
inline-closure path.

overrides[].finding_id / overrides[].finding_ids[] cross-check (SEC F-4):
whichever form is present on an override entry is cross-checked (after the
same NFC normalization and non-empty-string filter) against the SAME
known_findings map F-7 uses above. An id absent from both lenses is
"overrides[i].finding_id %r not found in lenses.*.findings[].id" (or the
finding_ids[j] analogue for the bulk form). Severity is deliberately NOT
examined here -- an override naming a CRITICAL finding is governed by the
orchestrator's own commit gate (orchestrator-protocol.md -> "Commit
creation", step 1: a review-blocked verdict commits only when overrides
carries one finding_id entry naming EVERY blocking CRITICAL, per
result-envelope.md -> "Review Receipt" -> the overrides bulk-form paragraph),
not this validator. An entry whose id is non-string, or whose finding_ids is
not a list, has no shape violation defined for that malformation today
(unchanged, out of scope for this lot) -- it is simply excluded from this
cross-check, never crashes it.

close.inline_closures: OPTIONAL on a ledger sidecar's close object -- absent
OR explicit null means no inline closures happened (every legacy sidecar
validates exactly as before this field existed). When present (and
non-null) it must be a list of { receipt, finding_ids } objects: receipt is
a non-empty, repo-relative path ENFORCED to end in ".json" that must exist
and be CONTAINED under project_root (the same _check_containment used for
receipt-mode file citations); finding_ids is a non-empty list of non-empty
strings, each compared -- after Unicode NFC normalization, mirroring
_check_duplicate_ids's own rationale -- against the cited receipt's own
findings_addressed[].finding_id values, themselves NFC-normalized the same
way. A finding_ids entry that fails the non-empty-string check (including a
non-hashable JSON array/object) is its own VIOLATION and is excluded from
the coverage comparison -- never a crash, never escalated to exit 2. Any
other failure here (missing/unreadable/unparsable/non-object cited receipt,
wrong extension) is likewise a VIOLATION (exit 1), never the exit-2
catch-all. A degenerate project_root (see above) short-circuits this whole
check before any cited receipt is opened -- the degenerate-root VIOLATION
is recorded and no further filesystem access is attempted in ledger mode.

close.commits: REQUIRED, unconditionally, whenever close is present as an
object -- must be a list, every entry a non-empty string, AND the list
itself must have at least 1 entry: a close recorded with zero commits is its
own VIOLATION ("close.commits must have at least 1 entry..."), regardless of
whether plan (below) is present, explicit null, or an empty list. This is
the sidecar-side mirror of orchestrator-protocol.md -> "Commit creation"
(one atomic commit created inline by the orchestrator, once per objective) --
a Close is never valid with zero commits recorded, plan tracked or not. When
plan IS a populated list, the length rule below (close.commits >= len(plan))
is a STRICTER floor stacked on top of this one, never a replacement for it.

plan: OPTIONAL on a ledger sidecar -- absent OR explicit null means "not
recorded" (every ledger sidecar written before this field existed, or any
Small task that never composed one, validates as before EXCEPT the
unconditional close.commits >= 1 floor, which applies plan or no plan).
When present it must be a list of { n, title, done } objects: n is a strict
integer forming the sequence 1..N in order (entry i has n == i+1 -- a gap, a
repeat, a wrong start, or an out-of-order value is ONE violation naming the
entry); title is a non-empty string; done is a strict boolean
(isinstance(v, bool) -- "yes"/1/0 are violations, never coerced). This is a
pure mirror of the Brief File's `## Plan` (the list) and `## Phases` (the
done flags) -- the .md sections stay authoritative, this field is only what
a script can check without parsing prose. TWO further invariants apply only
when close is present as an object (the gate's one prescribed invocation,
immediately before the status:done flip): every entry's done must be true
(each false entry is its own violation naming plan[i]); and, when
close.commits is a list, its length must be >= len(plan) (the orchestrator
creates at least one commit per done plan entry -- orchestrator-protocol.md
-> "Commit creation") -- STACKED on top of the unconditional close.commits
>= 1 rule above, never a replacement for it. Before close (absent or not an
object) neither of these two run. A ledger whose rows still carry a legacy
agent value from a retired commit-creation worker remains VALID -- ledger
rows are agnostic data this validator never inspects by agent name. NO
FILESYSTEM ACCESS: every plan check is a pure shape/arithmetic check over
already-parsed JSON, run unconditionally -- regardless of degenerate_root.
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


def _check_finding(where, finding, project_root, violations, skip_containment=False):
    """Validate one finding object. Returns (id, severity) -- either may be None.

    skip_containment (F-6): when the caller has already determined project_root
    is degenerate (validate_receipt's own root check), the on-disk resolution+
    existence half of the file-containment probe below is skipped -- it is the
    one sub-check that touches the filesystem, and running it against a
    degenerate root turns "does this finding's file exist" into an unbounded
    on-disk existence oracle (any absolute/traversal path resolves "contained"
    once the root is "/"). The pure-string os.path.isabs rejection on the same
    `file` field is NOT gated by skip_containment (REV F-5) -- it touches no
    filesystem, so it keeps running even under a degenerate root. Every other
    field on the finding (id, severity, confidence, evidence, line, claim,
    trigger) is likewise a pure shape check and keeps running regardless --
    mirrors validate_ledger's own short-circuit, scoped to the one on-disk
    probe."""
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
    elif os.path.isabs(file_field):
        # REV F-5: a pure string check -- touches no filesystem, so it is NOT
        # part of the on-disk probe skip_containment guards below and keeps
        # running even under a degenerate root.
        violations.append(
            "%s.file %r: absolute paths are not permitted as citations" % (where, file_field)
        )
    elif not skip_containment:
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


def _check_lens(lens_name, lenses, project_root, violations, skip_containment):
    """Walk one lens ('correctness' or 'security'). Returns (ids, any_critical,
    id_severities) -- id_severities is a list of (id, severity) pairs for every
    finding with a valid id, used by the findings_addressed cross-check (F-7)
    to know each candidate id's severity without re-walking the findings."""
    ids = []
    id_severities = []
    any_critical = False
    lens = lenses.get(lens_name)
    if lens is None:
        return ids, any_critical, id_severities
    if not isinstance(lens, dict):
        violations.append("lenses.%s must be an object" % lens_name)
        return ids, any_critical, id_severities

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
        fid, severity = _check_finding(where, finding, project_root, violations, skip_containment)
        if fid:
            ids.append(fid)
            id_severities.append((fid, severity))
        if severity == "CRITICAL":
            any_critical = True

    if status == "pass" and len(findings) > 0:
        violations.append(
            "lenses.%s.status is 'pass' but findings is non-empty (%d entries)"
            % (lens_name, len(findings))
        )
    if status == "findings" and len(findings) == 0:
        violations.append("lenses.%s.status is 'findings' but findings is empty" % lens_name)

    return ids, any_critical, id_severities


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


def _check_overrides(data, violations, known_findings):
    """known_findings: same {NFC-normalized id: severity} map F-7 uses
    (validate_receipt) -- backs the SEC F-4 cross-check below for BOTH the
    singular finding_id and the bulk finding_ids[] override forms. Severity
    is deliberately not examined here: an override naming a CRITICAL finding
    is governed by the orchestrator's own commit gate (orchestrator-protocol.md
    -> "Commit creation"), not this validator."""
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

        # SEC F-4: cross-check whichever single form is present against
        # known_findings. A non-string id, or a non-list finding_ids, has no
        # shape violation defined for it today (unchanged, out of scope for
        # this lot) -- it is simply excluded from this cross-check rather
        # than crashing it.
        if has_single and not has_bulk:
            finding_id = entry.get("finding_id")
            if isinstance(finding_id, str) and finding_id.strip():
                key = unicodedata.normalize("NFC", finding_id)
                if key not in known_findings:
                    violations.append(
                        "%s.finding_id %r not found in lenses.*.findings[].id" % (where, finding_id)
                    )
        elif has_bulk and not has_single:
            finding_ids = entry.get("finding_ids")
            if isinstance(finding_ids, list):
                for j, fid in enumerate(finding_ids):
                    if isinstance(fid, str) and fid.strip():
                        key = unicodedata.normalize("NFC", fid)
                        if key not in known_findings:
                            violations.append(
                                "%s.finding_ids[%d] %r not found in lenses.*.findings[].id"
                                % (where, j, fid)
                            )


def _check_findings_addressed(data, violations, known_findings):
    """known_findings: {NFC-normalized id: severity} built from BOTH lenses
    (validate_receipt) -- backs the F-7 cross-check below. F-7 is
    UNCONDITIONAL: it runs for every findings_addressed entry that carries a
    finding_id string, regardless of receipt kind (full/delta/fragment)."""
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
        finding_id = entry.get("finding_id")
        if not (isinstance(finding_id, str) and finding_id.strip()):
            # SEC F-1: one predicate rejects missing, null, empty, blank, and
            # non-string (e.g. a JSON number) finding_id alike -- this merges
            # what used to be a separate truthy-only "is required" check,
            # which a truthy non-string id (e.g. 42) could pass while also
            # skipping the F-7 cross-check below entirely.
            violations.append("%s.finding_id must be a non-empty string" % where)
        else:
            key = unicodedata.normalize("NFC", finding_id)
            if key not in known_findings:
                # REV F-4: membership, not a None-valued lookup -- an id that
                # IS present but whose finding failed its own severity-enum
                # check must never be reported as "not found".
                violations.append(
                    "%s.finding_id %r not found in lenses.*.findings[].id" % (where, finding_id)
                )
            elif known_findings[key] == "CRITICAL":
                violations.append(
                    "%s.finding_id %r names a CRITICAL finding -- inline closure is not permitted"
                    % (where, finding_id)
                )
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
    else:
        if not correctness_valid:
            violations.append(
                "lenses.correctness is required unless the top-level kind: \"security-fragment\" is declared"
            )

    correctness_ids, any_critical_correctness, correctness_severities = (
        _check_lens("correctness", lenses, project_root, violations, degenerate_root)
        if correctness_valid else ([], False, [])
    )
    security_ids, any_critical_security, security_severities = (
        _check_lens("security", lenses, project_root, violations, degenerate_root)
        if security_valid else ([], False, [])
    )

    _check_duplicate_ids(correctness_ids, security_ids, violations)

    # F-7: known_findings maps each valid finding id (NFC-normalized) to its
    # severity, across BOTH lenses -- the union findings_addressed[].finding_id
    # must resolve against. Last-writer-wins on an id collision is acceptable
    # here: a genuine id collision across lenses is already its own
    # duplicate-id violation above, so this map is never the sole signal.
    known_findings = {}
    for fid, severity in correctness_severities + security_severities:
        known_findings[unicodedata.normalize("NFC", fid)] = severity

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
    _check_overrides(data, violations, known_findings)
    _check_findings_addressed(data, violations, known_findings)

    return violations, infos


def _check_inline_closures(close, project_root, violations):
    """Validate close.inline_closures[] -- OPTIONAL: absent OR explicit null
    means no inline closures, and every legacy ledger sidecar (no such field,
    or an explicit null) validates exactly as it did before this field
    existed. When present, each entry cites a receipt sidecar (a repo-relative
    ".json" path that must exist, be CONTAINED under project_root) whose own
    findings_addressed[].finding_id values (NFC-normalized) must cover this
    entry's finding_ids (also NFC-normalized). A finding_ids entry that is not
    a non-empty string (including a non-hashable JSON array/object) is its own
    VIOLATION and is simply excluded from the coverage comparison -- never a
    crash. Any failure is a VIOLATION -- never escalated to exit 2, even when
    the cited receipt cannot be read or parsed."""
    entries = close.get("inline_closures")
    if entries is None:
        return
    if not isinstance(entries, list):
        violations.append("close.inline_closures must be a list when present")
        return

    for i, entry in enumerate(entries):
        where = "close.inline_closures[%d]" % i
        if not isinstance(entry, dict):
            violations.append("%s must be an object" % where)
            continue

        receipt = entry.get("receipt")
        if not isinstance(receipt, str) or not receipt.strip():
            violations.append("%s.receipt must be a non-empty string" % where)
            receipt = None
        elif not receipt.endswith(".json"):
            violations.append(
                "%s.receipt must be a repo-relative '.json' path (got %r)" % (where, receipt)
            )
            receipt = None

        finding_ids = entry.get("finding_ids")
        if not isinstance(finding_ids, list) or len(finding_ids) == 0:
            violations.append("%s.finding_ids must be a non-empty list" % where)
            finding_ids = []
        else:
            for j, fid in enumerate(finding_ids):
                if not isinstance(fid, str) or not fid.strip():
                    violations.append(
                        "%s.finding_ids[%d] must be a non-empty string" % (where, j)
                    )

        if receipt is None:
            continue

        ok, reason = _check_containment(project_root, receipt)
        if not ok:
            violations.append("%s.receipt %r: %s" % (where, receipt, reason))
            continue

        real_receipt = os.path.realpath(os.path.join(project_root, receipt))
        try:
            with open(real_receipt, "rb") as handle:
                raw = handle.read()
            receipt_data = json.loads(raw.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 -- fail closed as VIOLATION, never exit 2
            violations.append(
                "%s.receipt %r: could not be read/parsed as JSON (%s: %s)"
                % (where, receipt, type(exc).__name__, exc)
            )
            continue

        if not isinstance(receipt_data, dict):
            violations.append(
                "%s.receipt %r: top-level JSON value must be an object" % (where, receipt)
            )
            continue

        addressed = receipt_data.get("findings_addressed")
        covered_ids = set()
        if isinstance(addressed, list):
            for fa in addressed:
                if isinstance(fa, dict):
                    fid = fa.get("finding_id")
                    # Same "empty id" predicate as the ledger side's own
                    # finding_ids[] check above (isinstance + .strip()) --
                    # behaviour-neutral for every entry reachable today, since
                    # a finding_id that is a non-empty string but all
                    # whitespace was never a legitimate id either way.
                    if isinstance(fid, str) and fid.strip():
                        covered_ids.add(unicodedata.normalize("NFC", fid))

        # Membership test restricted to entries already validated as non-empty
        # strings above -- a non-string/unhashable finding_ids element (e.g. a
        # nested JSON array or object) already produced its own VIOLATION and
        # is simply excluded here, never handed to `in` on a set (which would
        # raise TypeError: unhashable type and abort the whole run at exit 2).
        string_ids = [fid for fid in finding_ids if isinstance(fid, str) and fid.strip()]
        if string_ids:
            missing = [
                fid for fid in string_ids
                if unicodedata.normalize("NFC", fid) not in covered_ids
            ]
            if missing:
                violations.append(
                    "%s: finding_ids %r not covered by %r's findings_addressed"
                    % (where, missing, receipt)
                )


def _check_plan(data, close, violations):
    """Validate the OPTIONAL top-level `plan` field -- see the module
    docstring's `plan` paragraph for the full contract. NO FILESYSTEM ACCESS:
    every rule below is a pure shape/arithmetic check over already-parsed
    JSON values, run unconditionally regardless of degenerate_root.

    close: data.get("close") as validate_ledger already computed it -- may be
    None, a non-dict, or a dict. The at-Close invariants (every entry done;
    enough close.commits entries) run ONLY when close is a dict; before close
    (absent or not an object) neither of them run, per D-C above.
    """
    plan = data.get("plan")
    if plan is None:
        return
    if not isinstance(plan, list):
        violations.append("plan must be a list when present")
        return

    close_is_dict = isinstance(close, dict)

    for i, entry in enumerate(plan):
        where = "plan[%d]" % i
        if not isinstance(entry, dict):
            violations.append("%s must be an object" % where)
            continue

        n = entry.get("n")
        if not _is_strict_int(n):
            violations.append("%s.n must be an integer (got %r)" % (where, n))
        elif n != i + 1:
            violations.append(
                "%s.n must be %d -- plan entries must number 1..N in order (got %r)"
                % (where, i + 1, n)
            )

        title = entry.get("title")
        if not isinstance(title, str) or not title:
            violations.append("%s.title must be a non-empty string" % where)

        done = entry.get("done")
        done_is_bool = isinstance(done, bool)
        if not done_is_bool:
            violations.append("%s.done must be a boolean (got %r)" % (where, done))
        elif close_is_dict and not done:
            violations.append(
                "%s.done must be true -- close is present but this entry is not done" % where
            )

    if close_is_dict:
        commits = close.get("commits")
        if isinstance(commits, list) and len(commits) < len(plan):
            violations.append(
                "plan has %d entries but close.commits has only %d entries (one brief, one "
                "commit)" % (len(plan), len(commits))
            )


def validate_ledger(data, project_root="."):
    violations = []

    real_root = os.path.realpath(project_root)
    degenerate_root = real_root == os.path.abspath(os.sep) or not os.path.isdir(real_root)
    if degenerate_root:
        violations.append(
            "project_root %r resolves to %r -- must be an existing directory other than the "
            "filesystem root (containment against the root is a tautology)" % (project_root, real_root)
        )

    ledger = data.get("ledger")
    if not isinstance(ledger, list):
        violations.append("ledger must be a list")
        ledger = []

    token_sum = 0
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
            # Unconditional invariant: close is present, so at least one
            # commit must be recorded -- independent of whether plan (below)
            # is present, null, or an empty list. The plan-based rule in
            # _check_plan (commits >= len(plan)) is a stricter floor that
            # stacks on top of this one when plan is a populated list; this
            # is the floor that still applies when plan cannot supply one.
            if len(commits) < 1:
                violations.append(
                    "close.commits must have at least 1 entry -- close is present, so "
                    "at least one commit must be recorded (orchestrator-protocol.md -> "
                    "\"Commit creation\")"
                )

        re_briefs = close.get("re_briefs")
        if not _is_strict_int(re_briefs) or re_briefs < 0:
            violations.append("close.re_briefs must be a non-negative integer (got %r)" % (re_briefs,))

        # A degenerate project_root already failed closed above; short-circuit
        # every check that would touch the filesystem rather than opening a
        # cited receipt against an unbounded root (SEC F-5).
        if not degenerate_root:
            _check_inline_closures(close, project_root, violations)

    # _check_plan runs unconditionally, regardless of degenerate_root -- every
    # plan rule is a pure shape/arithmetic check over already-parsed JSON, no
    # filesystem access at all (D-B).
    _check_plan(data, close, violations)

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
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Structural validator for the Review Receipt and Brief File ledger JSON sidecars.\n"
            "Modes:\n"
            "  receipt <file.json> [project_root]\n"
            "  ledger <file.json> [project_root]"
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
    ledger_parser.add_argument(
        "project_root",
        nargs="?",
        default=".",
        help="repo root close.inline_closures[].receipt entries resolve against (default: .)",
    )

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
            violations, infos = validate_ledger(data, args.project_root)
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
