#!/usr/bin/env python3
"""`ai-team <verb>` -- command line of the task state machine (domain/skills/_shared/machine.md).

Exit codes: 0 done · 1 refused (a condition is not met; the message names what is missing)
· 2 usage or I/O error.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_team import engram, hook  # noqa: E402
from ai_team.debt import fix as debt_fix  # noqa: E402
from ai_team.design import approve as approve_design, design_problems, load_design  # noqa: E402
from ai_team.machine import Machine, TICKET_KINDS  # noqa: E402
from ai_team.plan import (  # noqa: E402
    amend, build_inline_plan, build_plan, load_plan, load_scope_report, render_phase, render_plan, write_text,
)
from ai_team.receipt import validate_report  # noqa: E402
from ai_team.store import AI_TEAM_DIR, MachineError, Store, find_root  # noqa: E402


def _root(args):
    if args.root:
        root = os.path.realpath(args.root)
        if not os.path.isdir(os.path.join(root, AI_TEAM_DIR)):
            raise MachineError("%s has no %s/ directory" % (root, AI_TEAM_DIR), 2)
        return root
    root = find_root(os.getcwd())
    if root is None:
        raise MachineError("no %s/ directory found upward from %s -- this is not an ai-team project" % (AI_TEAM_DIR, os.getcwd()), 2)
    return root


def _task(store, task_id=None, allow_done=False):
    if task_id:
        return store.load(task_id)
    task = store.current()
    if task is None:
        if allow_done:
            done = [t for t in store.list_tasks() if t["status"] == "done"]
            if done:
                return done[-1]
        raise MachineError("no active task -- `ai-team status` shows what exists, `ai-team new <slug> --kind bounded|large` opens one")
    return task


def _sync_phases(task, plan):
    """The task JSON mirrors the plan's phases; attempts and commits survive a regeneration."""
    existing = {p["n"]: p for p in task["phases"]}
    phases = []
    for entry in plan["phases"]:
        old = existing.get(entry["n"])
        phases.append({
            "n": entry["n"],
            "title": entry["title"],
            "status": old["status"] if old else "pending",
            "attempts": old["attempts"] if old else 0,
            "tier": old["tier"] if old else None,
            "tier_reason": old["tier_reason"] if old else None,
            "commit": old["commit"] if old else None,
            "amendments": old["amendments"] if old else [],
        })
    task["phases"] = phases


# --- verbs -------------------------------------------------------------------------
def cmd_status(args):
    store = Store(_root(args))
    machine = Machine(store)
    task = store.load(args.task) if args.task else store.current()
    if args.json:
        payload = machine.status_json(task) if task else {"task": None, "moment": "classify", "card": machine.card_path("classify"),
                                                          "paused": [t["task"] for t in store.paused()]}
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    print(machine.status_text(task))
    paused = store.paused()
    if paused:
        print("Paused: %s" % ", ".join("%s (%s)" % (t["task"], t.get("pending_question") or "no question recorded") for t in paused))
    return 0


def cmd_new(args):
    store = Store(_root(args))
    design = None
    if args.design:
        design = store.rel(args.design)
        if not store.contained(design):
            raise MachineError("--design %s must live inside the project" % args.design, 2)
    task = store.new_task(args.slug, args.kind, design)
    print("created task %s (%s) at %s" % (task["task"], task["kind"], store.rel(store.task_path(task["task"]))))
    if args.kind == "large":
        print("next: scout-map pass → brainstorm → write .ai-team/designs/%s.md → `ai-team design approve <path>`" % task["task"])
    else:
        print("next: four approved lines → `ai-team plan generate --objective ... --decision ... --check ... --file ...`")
    return 0


def cmd_design_approve(args):
    store = Store(_root(args))
    rel = store.rel(args.path)
    if not store.contained(rel) or not os.path.isfile(store.abs(rel)):
        raise MachineError("design %s must be an existing file inside the project" % args.path, 2)
    design = approve_design(store.abs(rel))
    task = store.current()
    if task is not None and not task.get("design"):
        task["design"] = rel
        store.save(task)
    print("design %s approved (%d decisions, %d phases)" % (rel, len(design["decisions"]), len(design["phases"])))
    engram.mirror(
        "ai-team design approved: %s" % (design["title"] or rel),
        "Decisions:\n- " + "\n- ".join(design["decisions"]) + "\nPhases: " + "; ".join(p["title"] for p in design["phases"]),
        "decision", store.root,
    )
    return 0


def cmd_plan_generate(args):
    store = Store(_root(args))
    task = _task(store)
    machine = Machine(store)
    if machine.open_tickets(task):
        raise MachineError("settle the open tickets before regenerating the plan")
    if task["kind"] == "bounded" or args.objective:
        if task["kind"] == "large":
            raise MachineError("a large task generates its plan from the approved design, not from --objective")
        plan = build_inline_plan(task, args.objective, args.decision or [], args.check or [], args.out_of_scope or [], args.file or [])
        task["scope_report"] = None
        task["scope_skipped"] = plan["scope_skipped"]
    else:
        if not task.get("design"):
            raise MachineError("task has no design -- `ai-team design approve <path>` records it")
        design_rel = task["design"]
        design = load_design(store.abs(design_rel))
        problems = design_problems(design)
        if problems:
            raise MachineError("design %s is not ready:\n  - %s" % (design_rel, "\n  - ".join(problems)))
        scope = None
        scope_rel = args.scope and store.rel(args.scope) or task.get("scope_report")
        skipped = args.scope_skipped or (None if scope_rel else task.get("scope_skipped"))
        if scope_rel and not args.scope_skipped:
            if not store.contained(scope_rel) or not os.path.isfile(store.abs(scope_rel)):
                raise MachineError("scope report %s must be an existing file inside the project" % scope_rel, 2)
            scope = load_scope_report(store.abs(scope_rel))
        elif not skipped:
            raise MachineError("large task: pass --scope <scout report.md> (its final json block) or --scope-skipped \"<why the map pass already covers every file>\"")
        plan = build_plan(task, design, design_rel, scope=scope, scope_rel=scope_rel if scope else None, scope_skipped=None if scope else skipped)
        task["scope_report"] = scope_rel if scope else None
        task["scope_skipped"] = None if scope else skipped
    plan_rel = os.path.join(AI_TEAM_DIR, "plans", task["task"] + ".md")
    write_text(store.abs(plan_rel), render_plan(plan))
    task["plan"] = plan_rel
    _sync_phases(task, plan)
    store.save(task)
    print("plan written: %s (%d phase%s)" % (plan_rel, len(plan["phases"]), "" if len(plan["phases"]) == 1 else "s"))
    for phase in plan["phases"]:
        print("  phase %d — %s: %d files, %d checks" % (phase["n"], phase["title"], len(phase["expected_files"]), len(phase["acceptance_checks"])))
    return 0


def cmd_plan_amend(args):
    store = Store(_root(args))
    task = _task(store)
    if not task.get("plan"):
        raise MachineError("no plan to amend")
    plan = load_plan(store.abs(task["plan"]))
    amend(plan, args.phase, args.reason, args.file or [], args.check or [])
    write_text(store.abs(task["plan"]), render_plan(plan))
    Machine(store).phase(task, args.phase)["amendments"].append({"at": plan["phases"][args.phase - 1]["amendments"][-1]["at"], "reason": args.reason})
    store.save(task)
    print("phase %d amended: %s (re-run `ai-team phase extract %d`)" % (args.phase, args.reason, args.phase))
    return 0


def cmd_phase_extract(args):
    store = Store(_root(args))
    task = _task(store)
    if not task.get("plan"):
        raise MachineError("no plan -- `ai-team plan generate` first")
    plan = load_plan(store.abs(task["plan"]))
    out_rel = os.path.join(AI_TEAM_DIR, "plans", task["task"], "phase-%d.md" % args.n)
    write_text(store.abs(out_rel), render_phase(plan, args.n, task["plan"]))
    print(out_rel)
    return 0


def cmd_phase_done(args):
    store = Store(_root(args))
    task = _task(store)
    phase = Machine(store).phase_done(task, args.n, args.commit)
    print("phase %d committed: %s" % (args.n, phase["commit"]))
    return 0


def cmd_tier(args):
    store = Store(_root(args))
    task = _task(store)
    phase = Machine(store).declare_tier(task, args.phase, args.tier, args.reason)
    print("phase %d: tier %d (%s)" % (args.phase, phase["tier"], phase["tier_reason"]))
    return 0


def cmd_acquire(args):
    store = Store(_root(args))
    task = _task(store, args.task, allow_done=(args.kind == "retro"))
    machine = Machine(store)
    ticket = machine.acquire(task, args.kind, args.phase)
    line = "ticket %s issued: %s" % (ticket["id"], ticket["kind"])
    if ticket["phase"] is not None:
        line += " phase %d attempt %s" % (ticket["phase"], ticket["attempt"])
    print(line)
    hint = machine.attempt_hint(ticket["kind"], ticket["attempt"])
    if hint:
        print(hint)
    print("settle with: ai-team settle %s --outcome <ok|warning|needs_input|blocked|failed|infra-death> --model <m> --tokens <n> --tool-uses <n> --duration <s>%s"
          % (ticket["id"], " --report <path.md>" if ticket["kind"] in ("reviewer", "security-audit", "scout-scope", "scout-map") else ""))
    return 0


def cmd_settle(args):
    store = Store(_root(args))
    task = _task(store, args.task, allow_done=True)
    ticket, notes = Machine(store).settle(
        task, args.ticket, args.outcome, model=args.model, tokens=args.tokens, tool_uses=args.tool_uses,
        duration_s=args.duration, report=args.report, defer=[d for d in (args.defer or "").split(",") if d],
    )
    line = "ticket %s settled: %s" % (ticket["id"], ticket["outcome"])
    if ticket["verdict"]:
        line += " · verdict %s · %d finding(s)" % (ticket["verdict"], len(ticket["findings"] or []))
    print(line)
    for note in notes:
        print(note)
    return 0


def cmd_ruling(args):
    store = Store(_root(args))
    task = _task(store)
    entry = Machine(store).ruling(task, args.ticket, args.finding, args.text, args.cost_if_wrong)
    print("ruling recorded for %s %s at %s" % (entry["ticket"], entry["finding"], entry["at"]))
    return 0


def cmd_commit_check(args):
    store = Store(_root(args))
    task = _task(store)
    ok, reasons = Machine(store).commit_check(task, args.phase)
    if ok:
        print("phase %d may be committed -- stage its files, `git commit`, then `ai-team phase done %d --commit <hash>`" % (args.phase, args.phase))
        return 0
    print("phase %d may NOT be committed:" % args.phase)
    for reason in reasons:
        print("  - " + reason)
    return 1


def cmd_debt_fix(args):
    store = Store(_root(args))
    flipped = debt_fix(os.path.join(store.ai_team, "tech-debt.md"), args.match, args.commit)
    print("%d row(s) flipped to fixed (%s)" % (flipped, args.commit))
    return 0 if flipped else 1


def cmd_pause(args):
    store = Store(_root(args))
    task = _task(store)
    Machine(store).pause(task, args.question)
    print("task %s paused%s" % (task["task"], " · question: %s" % args.question if args.question else ""))
    return 0


def cmd_resume(args):
    store = Store(_root(args))
    if args.task:
        task = store.load(args.task)
    else:
        paused = store.paused()
        if len(paused) != 1:
            raise MachineError("say which task: %s" % (", ".join(t["task"] for t in paused) or "none paused"))
        task = paused[0]
    Machine(store).resume(task)
    print("task %s resumed" % task["task"])
    return 0


def cmd_close(args):
    store = Store(_root(args))
    task = _task(store)
    balance = Machine(store).close(task)
    print("task %s done · %d tickets · %d tokens · %d attempts" % (task["task"], balance["tickets"], balance["tokens"], balance["attempts"]))
    print("next: `ai-team acquire retro` when a retrospective is wanted")
    return 0


def cmd_receipt_check(args):
    code, out, err, _ = validate_report(args.file, args.project_root)
    for line in out:
        print(line)
    for line in err:
        sys.stderr.write(line + "\n")
    return code


def cmd_hook(args):
    return hook.main(args.event)


# --- parser ------------------------------------------------------------------------
def build_parser():
    parser = argparse.ArgumentParser(prog="ai-team", description="ai-team task state machine (see _shared/machine.md)")
    parser.add_argument("--root", help="project root (default: walk up from the working directory to .ai-team/)")
    sub = parser.add_subparsers(dest="verb", required=True)

    p = sub.add_parser("status", help="task in progress and what is allowed now")
    p.add_argument("--json", action="store_true")
    p.add_argument("--task")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("new", help="create a task")
    p.add_argument("slug")
    p.add_argument("--kind", choices=("bounded", "large"), required=True)
    p.add_argument("--design")
    p.set_defaults(func=cmd_new)

    design = sub.add_parser("design", help="design verbs").add_subparsers(dest="design_verb", required=True)
    p = design.add_parser("approve", help="flip a design to approved (after the user's yes)")
    p.add_argument("path")
    p.set_defaults(func=cmd_design_approve)

    plan = sub.add_parser("plan", help="plan verbs").add_subparsers(dest="plan_verb", required=True)
    p = plan.add_parser("generate", help="generate the plan from the design (+ scope report) or four inline lines")
    p.add_argument("--scope", help="scout scope report (.md with a final json block)")
    p.add_argument("--scope-skipped", help="why the scope pass is skipped")
    p.add_argument("--objective")
    p.add_argument("--decision", action="append")
    p.add_argument("--check", action="append")
    p.add_argument("--out-of-scope", action="append")
    p.add_argument("--file", action="append")
    p.set_defaults(func=cmd_plan_generate)
    p = plan.add_parser("amend", help="widen a phase with a recorded reason")
    p.add_argument("--phase", type=int, required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--file", action="append")
    p.add_argument("--check", action="append")
    p.set_defaults(func=cmd_plan_amend)

    phase = sub.add_parser("phase", help="phase verbs").add_subparsers(dest="phase_verb", required=True)
    p = phase.add_parser("extract", help="write the implementer's phase file")
    p.add_argument("n", type=int)
    p.set_defaults(func=cmd_phase_extract)
    p = phase.add_parser("done", help="record the phase's commit")
    p.add_argument("n", type=int)
    p.add_argument("--commit", required=True)
    p.set_defaults(func=cmd_phase_done)

    p = sub.add_parser("tier", help="declare the evidence tier of a phase's diff")
    p.add_argument("tier", type=int, choices=(0, 1, 2))
    p.add_argument("--phase", type=int, required=True)
    p.add_argument("--reason", required=True)
    p.set_defaults(func=cmd_tier)

    p = sub.add_parser("acquire", help="ask for a ticket")
    p.add_argument("kind", choices=TICKET_KINDS)
    p.add_argument("--phase", type=int)
    p.add_argument("--task")
    p.set_defaults(func=cmd_acquire)

    p = sub.add_parser("settle", help="close a ticket with the harness figures")
    p.add_argument("ticket")
    p.add_argument("--outcome", required=True)
    p.add_argument("--model")
    p.add_argument("--tokens", type=int)
    p.add_argument("--tool-uses", type=int)
    p.add_argument("--duration", type=int)
    p.add_argument("--report")
    p.add_argument("--defer", help="comma-separated finding ids to park in tech-debt.md")
    p.add_argument("--task")
    p.set_defaults(func=cmd_settle)

    p = sub.add_parser("ruling", help="adjudicate one open finding")
    p.add_argument("ticket")
    p.add_argument("--finding", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--cost-if-wrong", required=True)
    p.set_defaults(func=cmd_ruling)

    p = sub.add_parser("commit-check", help="exit 0 when the phase may be committed")
    p.add_argument("--phase", type=int, required=True)
    p.set_defaults(func=cmd_commit_check)

    debt = sub.add_parser("debt", help="tech-debt verbs").add_subparsers(dest="debt_verb", required=True)
    p = debt.add_parser("fix", help="flip matching open rows to fixed (<hash>)")
    p.add_argument("--match", required=True)
    p.add_argument("--commit", required=True)
    p.set_defaults(func=cmd_debt_fix)

    p = sub.add_parser("pause", help="park the active task")
    p.add_argument("--question")
    p.set_defaults(func=cmd_pause)
    p = sub.add_parser("resume", help="reactivate a paused task")
    p.add_argument("task", nargs="?")
    p.set_defaults(func=cmd_resume)
    p = sub.add_parser("close", help="every phase committed → done")
    p.set_defaults(func=cmd_close)

    receipt = sub.add_parser("receipt", help="receipt verbs").add_subparsers(dest="receipt_verb", required=True)
    p = receipt.add_parser("check", help="validate a review report's receipt block")
    p.add_argument("file")
    p.add_argument("project_root", nargs="?", default=".")
    p.set_defaults(func=cmd_receipt_check)

    p = sub.add_parser("hook", help="Claude Code hook entry point (JSON on stdin)")
    p.add_argument("event", choices=("pre-tool-use", "session-start"))
    p.set_defaults(func=cmd_hook)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except MachineError as exc:
        sys.stderr.write("ai-team: %s\n" % exc)
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
