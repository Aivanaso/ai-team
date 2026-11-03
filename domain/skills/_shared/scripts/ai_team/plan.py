"""The plan: generated from the approved design plus the scout's scope report, never
written by the orchestrator. `.ai-team/plans/<task>.md` is Markdown for humans whose final
fenced ```json block is the object the machine reads back; `phase extract` writes the
implementer's input from that object.
"""

import os

from ai_team.calibration import check_line, demotion_question, is_calibrated, state_note, validate_check, validate_scope_checks
from ai_team.config import mirror_path, required_mirror_rules
from ai_team.fenced import load_json_block, render_json_block
from ai_team.store import MachineError, atomic_write, utc_now


def compute_roots(paths):
    """Union of containing directories; a top-level file contributes no root."""
    roots = set()
    for path in paths:
        normalized = path[2:] if path.startswith("./") else path
        if "/" in normalized:
            roots.add(os.path.dirname(normalized))
    return sorted(roots)


def add_test_mirrors(files, rules, root):
    """`files` extended with the test mirror of each path a rule matches. A mirror already listed
    keeps its entry (the scout's evidence wins); one present under `root` is a MODIFY, else a CREATE."""
    known = {f["path"][2:] if f["path"].startswith("./") else f["path"] for f in files}
    extended = list(files)
    for entry in files:
        mirror = mirror_path(entry["path"], rules)
        if mirror is None or mirror in known:
            continue
        known.add(mirror)
        extended.append({
            "action": "MODIFY" if os.path.isfile(os.path.join(root, mirror)) else "CREATE",
            "path": mirror,
            "evidence": "test mirror of %s (config structure.test_mirror)" % entry["path"],
        })
    return extended


def load_scope_report(path):
    data, error = load_json_block(path)
    if error is not None:
        raise MachineError("scope report %s: %s" % (path, error[1]))
    if not isinstance(data, dict) or data.get("kind") != "scope-report":
        raise MachineError('scope report %s: its json block must be {"kind": "scope-report", "phases": [...]}' % path)
    phases = data.get("phases")
    if not isinstance(phases, list):
        raise MachineError("scope report %s: phases must be a list" % path)
    by_n = {}
    for i, entry in enumerate(phases):
        if not isinstance(entry, dict) or not isinstance(entry.get("n"), int):
            raise MachineError("scope report %s: phases[%d] must be an object with an integer n" % (path, i))
        by_n[entry["n"]] = entry
    violations = validate_scope_checks(by_n)
    if violations:
        raise MachineError("scope report %s does not validate:\n  - %s" % (path, "\n  - ".join(violations)))
    return by_n


def _run_checks(runner, checks, phase_n, source):
    """Calibrate CLI-declared checks by running them: `checks` is a list of (command, failure)."""
    entries, notes = [], []
    for command, failure in checks:
        entry = runner(command, failure)
        entries.append(entry)
        note = state_note(entry, phase_n, source)
        if note:
            notes.append(note)
    return entries, notes


def _scoped_checks(scoped, phase_n):
    """The scout's calibrated checks, plus the open question each un-run check becomes."""
    entries, questions, notes = [], [], []
    for i, raw in enumerate(scoped.get("acceptance_checks") or []):
        check, violations = validate_check(raw, "phase %d acceptance_checks[%d]" % (phase_n, i))
        if violations:
            raise MachineError("scope report phase %d does not validate:\n  - %s" % (phase_n, "\n  - ".join(violations)))
        if is_calibrated(check):
            entries.append(check)
            note = state_note(check, phase_n, "scout")
            if note:
                notes.append(note)
        else:
            question = demotion_question(check, phase_n)
            questions.append(question)
            notes.append("phase %d: %s" % (phase_n, question))
    return entries, questions, notes


def build_plan(task, design, design_rel, scope=None, scope_rel=None, scope_skipped=None, runner=None, *, config):
    """The plan object plus the lines `plan generate` prints (red-today checks, demoted checks).
    With a scope report the scout's calibrations are used; without one (`--scope-skipped`) the
    machine runs the design's checks through `runner(command, failure)`. Under strict TDD each
    phase's files gain their test mirrors (`config`); a strict project without a mirror is refused."""
    rules = required_mirror_rules(config)
    constraints = list(design["decisions"]) + ["security: %s" % m for m in design["security_measures"]]
    phases, notes = [], []
    for phase in design["phases"]:
        entry = {
            "n": phase["n"],
            "title": phase["title"],
            "objective": phase["delivers"] or phase["title"],
            "scenarios": list(phase["scenarios"]),
            "acceptance_checks": [],
            "expected_files": list(design["surfaces"]),
            "scout_notes": [],
            "open_questions": [],
            "amendments": [],
        }
        if scope is None:
            entry["acceptance_checks"], phase_notes = _run_checks(runner, [(c, None) for c in phase["checks"]], phase["n"], "design")
            notes += phase_notes
        else:
            scoped = scope.get(phase["n"])
            if scoped is None:
                raise MachineError("scope report has no entry for phase %d -- every design phase must appear" % phase["n"])
            files = scoped.get("expected_files") or []
            if not isinstance(files, list) or not isinstance(scoped.get("acceptance_checks") or [], list):
                raise MachineError("scope report phase %d: expected_files and acceptance_checks must be lists" % phase["n"])
            if files:
                entry["expected_files"] = [
                    {"action": f.get("action", "MODIFY"), "path": f.get("path"), "evidence": f.get("evidence", "")}
                    for f in files if isinstance(f, dict) and f.get("path")
                ]
            entry["scout_notes"] = [str(c) for c in scoped.get("constraints_candidates") or []]
            entry["open_questions"] = [str(q) for q in scoped.get("open_questions") or []]
            checks, questions, phase_notes = _scoped_checks(scoped, phase["n"])
            if phase["checks"] and not checks and not questions and not entry["open_questions"]:
                raise MachineError(
                    "scope report phase %d: the design's checks (%s) were neither calibrated nor questioned -- "
                    "the scout calibrates each one or lists the gap in open_questions"
                    % (phase["n"], ", ".join("`%s`" % c for c in phase["checks"])))
            entry["acceptance_checks"] = checks
            entry["open_questions"] += questions
            notes += phase_notes
        entry["expected_files"] = add_test_mirrors(entry["expected_files"], rules, config.root)
        entry["allowed_edit_roots"] = compute_roots([f["path"] for f in entry["expected_files"]])
        phases.append(entry)
    return {
        "kind": "plan",
        "task": task["task"],
        "generated_at": utc_now(),
        "design": design_rel,
        "scope_report": scope_rel,
        "scope_skipped": scope_skipped,
        "title": design["title"] or task["task"],
        "objective": design["objective"],
        "constraints": constraints,
        "out_of_scope": list(design["out_of_scope"]),
        "phases": phases,
    }, notes


def build_inline_plan(task, objective, decisions, checks, out_of_scope, files, runner, config):
    """The bounded plan plus its notes; `checks` is a list of (command, failure) the machine runs.
    Under strict TDD the files gain their test mirrors (`config`)."""
    if not objective or not checks:
        raise MachineError("a bounded plan needs --objective and at least one --check")
    rules = required_mirror_rules(config)
    expected = add_test_mirrors(
        [{"action": "MODIFY", "path": f, "evidence": "user-approved in chat"} for f in files], rules, config.root)
    entries, notes = _run_checks(runner, checks, 1, "orchestrator")
    return {
        "kind": "plan",
        "task": task["task"],
        "generated_at": utc_now(),
        "design": None,
        "scope_report": None,
        "scope_skipped": "bounded task: four approved lines in chat",
        "title": objective,
        "objective": objective,
        "constraints": list(decisions),
        "out_of_scope": list(out_of_scope),
        "phases": [{
            "n": 1,
            "title": objective,
            "objective": objective,
            "scenarios": [],
            "acceptance_checks": entries,
            "expected_files": expected,
            "allowed_edit_roots": compute_roots([f["path"] for f in expected]),
            "scout_notes": [],
            "open_questions": [],
            "amendments": [],
        }],
    }, notes


def _bullets(items, empty="- (none)"):
    return "\n".join("- %s" % item for item in items) if items else empty


def render_plan(plan):
    out = [
        "---",
        "task: %s" % plan["task"],
        "generated_at: %s" % plan["generated_at"],
        "design: %s" % (plan["design"] or "none"),
        "scope_report: %s" % (plan["scope_report"] or "none"),
        "---",
        "",
        "# Plan — %s" % plan["title"],
        "",
        "> Generated by `ai-team plan generate`; edit the design or run `ai-team plan amend`, never this file by hand.",
        "",
        "## Objective",
        "",
        plan["objective"],
        "",
        "## Constraints (the design's decisions, verbatim)",
        "",
        _bullets(plan["constraints"]),
        "",
        "## Out of scope",
        "",
        _bullets(plan["out_of_scope"]),
        "",
    ]
    for phase in plan["phases"]:
        out += [
            "## Phase %d — %s" % (phase["n"], phase["title"]),
            "",
            "**Objective**: %s" % phase["objective"],
            "",
            "**Scenarios**",
            "",
            _bullets(phase["scenarios"]),
            "",
            "**Acceptance checks**",
            "",
            _bullets([check_line(c) for c in phase["acceptance_checks"]]),
            "",
            "**Expected files**",
            "",
            _bullets(["%s `%s` (%s)" % (f["action"], f["path"], f["evidence"]) for f in phase["expected_files"]]),
            "",
            "**Allowed edit roots**: %s" % (", ".join("`%s`" % r for r in phase["allowed_edit_roots"]) or "(top-level files only)"),
            "",
        ]
        if phase["scout_notes"]:
            out += ["**Scout notes (candidate constraints, anchored)**", "", _bullets(phase["scout_notes"]), ""]
        if phase["open_questions"]:
            out += ["**Open questions**", "", _bullets(phase["open_questions"]), ""]
        if phase["amendments"]:
            out += ["**Amendments**", "", _bullets(["%s — %s" % (a["at"], a["reason"]) for a in phase["amendments"]]), ""]
    out += ["## Machine block", "", render_json_block(plan)]
    return "\n".join(out)


def load_plan(path):
    data, error = load_json_block(path)
    if error is not None:
        raise MachineError("plan %s: %s" % (path, error[1]), 2)
    if not isinstance(data, dict) or data.get("kind") != "plan":
        raise MachineError("plan %s: its json block is not a plan object" % path, 2)
    return data


def phase_of(plan, n):
    for phase in plan["phases"]:
        if phase["n"] == n:
            return phase
    raise MachineError("plan has no phase %d (phases: 1..%d)" % (n, len(plan["phases"])))


def amend(plan, n, reason, files, checks, runner, config):
    """Widen a phase; `checks` is a list of (command, failure) the machine runs before the
    plan changes, so a check that times out or does zero work leaves the plan untouched.
    Under strict TDD the added files gain their test mirrors (`config`)."""
    rules = required_mirror_rules(config)
    phase = phase_of(plan, n)
    entries, notes = _run_checks(runner, checks, n, "orchestrator")
    known = {f["path"] for f in phase["expected_files"]}
    for path in files:
        if path not in known:
            phase["expected_files"].append({"action": "MODIFY", "path": path, "evidence": "amendment: %s" % reason})
    phase["expected_files"] = add_test_mirrors(phase["expected_files"], rules, config.root)
    phase["acceptance_checks"] += entries
    phase["allowed_edit_roots"] = compute_roots([f["path"] for f in phase["expected_files"]])
    phase["amendments"].append({"at": utc_now(), "reason": reason, "files": list(files), "checks": [c for c, _ in checks]})
    return phase, notes


def amend_decisions(plan, n, reason, decisions):
    """Append mid-task design decisions verbatim to the plan's constraints and record them on phase n.
    A text the plan already holds is refused before anything changes."""
    phase = phase_of(plan, n)
    for index, decision in enumerate(decisions):
        if decision in plan["constraints"] or decision in decisions[:index]:
            raise MachineError("decision %r is already a constraint of the plan -- amend with a decision the plan does not hold" % decision)
    plan["constraints"] += list(decisions)
    phase["amendments"].append({"at": utc_now(), "reason": reason, "files": [], "checks": [], "decisions": list(decisions)})
    return phase


def render_phase(plan, n, plan_rel):
    phase = phase_of(plan, n)
    brief = {
        "kind": "phase",
        "task": plan["task"],
        "plan": plan_rel,
        "design": plan["design"],
        "phase": n,
        "title": phase["title"],
        "objective": phase["objective"],
        "task_objective": plan["objective"],
        "constraints": plan["constraints"],
        "out_of_scope": plan["out_of_scope"],
        "scenarios": phase["scenarios"],
        "acceptance_checks": phase["acceptance_checks"],
        "expected_files": phase["expected_files"],
        "allowed_edit_roots": phase["allowed_edit_roots"],
        "scout_notes": phase["scout_notes"],
        "open_questions": phase["open_questions"],
        "amendments": phase["amendments"],
    }
    out = [
        "# Phase %d of %d — %s" % (n, len(plan["phases"]), phase["title"]),
        "",
        "Task `%s` · plan `%s` · design %s" % (plan["task"], plan_rel, "`%s`" % plan["design"] if plan["design"] else "none (bounded)"),
        "",
        "## Objective",
        "",
        phase["objective"],
        "",
        "Task objective: %s" % plan["objective"],
        "",
        "## Constraints (invariants, never mechanisms)",
        "",
        _bullets(plan["constraints"]),
        "",
        "## Scenarios (given / when / then)",
        "",
        _bullets(phase["scenarios"]),
        "",
        "## Acceptance checks (run verbatim, in order)",
        "",
        "Each line records what the command did BEFORE this phase (its calibration) and, after the dash, what it must do when the phase is done (`expect`). A check red today is this phase's own gap to close.",
        "",
        _bullets([check_line(c) for c in phase["acceptance_checks"]]),
        "",
        "## Expected files",
        "",
        _bullets(["%s `%s` (%s)" % (f["action"], f["path"], f["evidence"]) for f in phase["expected_files"]]),
        "",
        "## Allowed edit roots",
        "",
        _bullets(["`%s`" % r for r in phase["allowed_edit_roots"]], "- (top-level files only, each permitted by its own declaration)"),
        "",
        "## Out of scope",
        "",
        _bullets(plan["out_of_scope"]),
        "",
    ]
    if phase["scout_notes"]:
        out += ["## Scout notes", "", _bullets(phase["scout_notes"]), ""]
    if phase["amendments"]:
        out += ["## Amendments", "", _bullets(["%s — %s" % (a["at"], a["reason"]) for a in phase["amendments"]]), ""]
    out += ["## Machine block", "", render_json_block(brief)]
    return "\n".join(out)


def write_text(path, text):
    atomic_write(path, text)
