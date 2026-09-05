"""The plan: generated from the approved design plus the scout's scope report, never
written by the orchestrator. `.ai-team/plans/<task>.md` is Markdown for humans whose final
fenced ```json block is the object the machine reads back; `phase extract` writes the
implementer's input from that object.
"""

import os

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
    return by_n


def _check_entries(commands):
    return [{"command": c, "expect": "exit 0", "verified": "from the design"} for c in commands]


def build_plan(task, design, design_rel, scope=None, scope_rel=None, scope_skipped=None):
    constraints = list(design["decisions"]) + ["security: %s" % m for m in design["security_measures"]]
    phases = []
    for phase in design["phases"]:
        entry = {
            "n": phase["n"],
            "title": phase["title"],
            "objective": phase["delivers"] or phase["title"],
            "scenarios": list(phase["scenarios"]),
            "acceptance_checks": _check_entries(phase["checks"]),
            "expected_files": list(design["surfaces"]),
            "scout_notes": [],
            "open_questions": [],
            "amendments": [],
        }
        if scope is not None:
            scoped = scope.get(phase["n"])
            if scoped is None:
                raise MachineError("scope report has no entry for phase %d -- every design phase must appear" % phase["n"])
            files = scoped.get("expected_files") or []
            checks = scoped.get("acceptance_checks") or []
            if not isinstance(files, list) or not isinstance(checks, list):
                raise MachineError("scope report phase %d: expected_files and acceptance_checks must be lists" % phase["n"])
            if files:
                entry["expected_files"] = [
                    {"action": f.get("action", "MODIFY"), "path": f.get("path"), "evidence": f.get("evidence", "")}
                    for f in files if isinstance(f, dict) and f.get("path")
                ]
            if checks:
                entry["acceptance_checks"] = [
                    {"command": c.get("command"), "expect": c.get("expect", "exit 0"), "verified": c.get("verified", "")}
                    for c in checks if isinstance(c, dict) and c.get("command")
                ]
            entry["scout_notes"] = [str(c) for c in scoped.get("constraints_candidates") or []]
            entry["open_questions"] = [str(q) for q in scoped.get("open_questions") or []]
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
    }


def build_inline_plan(task, objective, decisions, checks, out_of_scope, files):
    if not objective or not checks:
        raise MachineError("a bounded plan needs --objective and at least one --check")
    expected = [{"action": "MODIFY", "path": f, "evidence": "user-approved in chat"} for f in files]
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
            "acceptance_checks": _check_entries(checks),
            "expected_files": expected,
            "allowed_edit_roots": compute_roots(files),
            "scout_notes": [],
            "open_questions": [],
            "amendments": [],
        }],
    }


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
            _bullets(["`%s` — %s" % (c["command"], c["expect"]) for c in phase["acceptance_checks"]]),
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


def amend(plan, n, reason, files, checks):
    phase = phase_of(plan, n)
    known = {f["path"] for f in phase["expected_files"]}
    for path in files:
        if path not in known:
            phase["expected_files"].append({"action": "MODIFY", "path": path, "evidence": "amendment: %s" % reason})
    for command in checks:
        phase["acceptance_checks"].append({"command": command, "expect": "exit 0", "verified": "amendment: %s" % reason})
    phase["allowed_edit_roots"] = compute_roots([f["path"] for f in phase["expected_files"]])
    phase["amendments"].append({"at": utc_now(), "reason": reason, "files": list(files), "checks": list(checks)})
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
        _bullets(["`%s` — %s" % (c["command"], c["expect"]) for c in phase["acceptance_checks"]]),
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
