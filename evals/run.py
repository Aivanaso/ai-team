#!/usr/bin/env python3
"""evals/run.py -- layer-3 tests: does the ORCHESTRATOR obey, with a real (cheap) model?

Each case under evals/cases/<name>/ is a prompt against a throwaway copy of its fixture
project, run twice: `without` the rule (no hooks, no stub in CLAUDE.md) and `with` it. The
organic-* agents are replaced by stubs (`--agents`) that write a marker file and answer
"ok", so only the orchestrator is under test. Graders read three sources -- the stream-json
events (Agent tool uses and their subagent_type), the disk (.ai-team/tasks, plans, stub
markers) and the hook denials -- never the model's prose.

A grader that FAILS without the rule and PASSES with it is RED/GREEN: the rule is doing
work. Run by hand or nightly; each run costs real tokens.

    python3 evals/run.py                      # every case, both variants
    python3 evals/run.py bounded-hazlo-ya     # one case
    python3 evals/run.py --variant with --repeat 3 --keep

Requires `claude` on PATH. Runs `claude -p` with --dangerously-skip-permissions inside the
temp copy (the hooks' deny still wins over that flag), --setting-sources project so the
user's own settings stay out, and --max-turns as a cost ceiling.
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SCRIPTS = os.path.join(REPO, "domain", "skills", "_shared", "scripts")
LAUNCHER = os.path.join(SCRIPTS, "ai-team")
STUB_TEMPLATE = os.path.join(REPO, "adapters", "claude-code", "templates", "CLAUDE.md")
AGENTS_FILE = os.path.join(HERE, "stubs", "agents.json")
CASES_DIR = os.path.join(HERE, "cases")
DENY_MARK = "ai-team: no"


def sh(command, cwd, env=None, check=True, stdin=None):
    return subprocess.run(command, cwd=cwd, env=env, input=stdin, capture_output=True, text=True, check=check)


def settings_for(variant):
    if variant == "without":
        return {"permissions": {"defaultMode": "bypassPermissions"}}
    with open(os.path.join(REPO, "adapters", "claude-code", "templates", "hooks.json")) as handle:
        hooks = json.load(handle)["hooks"]
    for groups in hooks.values():
        for group in groups:
            for hook in group["hooks"]:
                hook["command"] = hook["command"].replace('"$HOME/.claude/skills/_shared/scripts/ai-team"', '"%s"' % LAUNCHER)
    return {"permissions": {"defaultMode": "bypassPermissions"}, "hooks": hooks}


def claude_md_for(variant):
    if variant == "without":
        return "# Fixture project\n\nNo orchestration rules installed.\n"
    with open(STUB_TEMPLATE) as handle:
        stub = handle.read()
    return stub.replace("~/.claude/skills/_shared", os.path.join(REPO, "domain", "skills", "_shared"))


def prepare(case_dir, variant, keep):
    work = tempfile.mkdtemp(prefix="ai-team-eval-")
    project = os.path.join(work, "project")
    shutil.copytree(os.path.join(case_dir, "fixture"), project)
    os.makedirs(os.path.join(project, ".ai-team"), exist_ok=True)
    os.makedirs(os.path.join(project, ".claude"), exist_ok=True)
    with open(os.path.join(project, ".claude", "settings.json"), "w") as handle:
        json.dump(settings_for(variant), handle, indent=2)
    with open(os.path.join(project, "CLAUDE.md"), "w") as handle:
        handle.write(claude_md_for(variant))
    git = ["git", "-c", "user.email=eval@ai-team", "-c", "user.name=eval"]
    sh(["git", "init", "-q"], project)
    sh(git + ["add", "-A"], project)
    sh(git + ["commit", "-qm", "fixture"], project)
    head = sh(["git", "rev-parse", "HEAD"], project).stdout.strip()
    return work, project, head


def seed(project, commands, head):
    env = dict(os.environ, PATH=SCRIPTS + os.pathsep + os.environ.get("PATH", ""))
    for command in commands:
        rendered = command.replace("{head}", head)
        completed = subprocess.run(rendered, shell=True, cwd=project, env=env, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError("seed command failed: %s\n%s%s" % (rendered, completed.stdout, completed.stderr))


def run_session(project, prompt, model, effort, max_turns):
    with open(AGENTS_FILE) as handle:
        agents = handle.read()
    command = [
        "claude", "-p", prompt, "--model", model, "--effort", effort, "--setting-sources", "project",
        "--output-format", "stream-json", "--verbose", "--include-hook-events", "--agents", agents,
        "--dangerously-skip-permissions", "--max-turns", str(max_turns),
    ]
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    env["PATH"] = SCRIPTS + os.pathsep + env.get("PATH", "")
    completed = subprocess.run(command, cwd=project, env=env, capture_output=True, text=True, check=False)
    events = []
    for line in completed.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except ValueError:
            events.append({"type": "raw", "text": line})
    return completed.returncode, events, completed.stderr


def agent_launches(events):
    launches = []
    for event in events:
        message = event.get("message") if isinstance(event, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Agent":
                launches.append(block.get("input") or {})
    return launches


def deny_count(events):
    """Blocked launches: one per tool_result the model received carrying a deny reason; when
    the stream carries no tool_result shape at all, any event mentioning the mark counts once."""
    results = 0
    mentions = 0
    for event in events:
        text = json.dumps(event, ensure_ascii=False)
        if DENY_MARK not in text:
            continue
        mentions += 1
        if isinstance(event, dict) and event.get("type") == "user":
            results += 1
    return results if results else min(mentions, 1)


def final_text(events):
    for event in reversed(events):
        if isinstance(event, dict) and event.get("type") == "result":
            return event.get("result") or ""
    return ""


def load_task(project):
    files = sorted(glob.glob(os.path.join(project, ".ai-team", "tasks", "*.json")))
    if not files:
        return None
    with open(files[-1]) as handle:
        return json.load(handle)


def grade(grader, project, events):
    kind = grader["kind"]
    if kind == "file_exists":
        return bool(glob.glob(os.path.join(project, grader["glob"]))), grader["glob"]
    if kind == "agent_launched":
        wanted = grader.get("subagent_type")
        count = sum(1 for launch in agent_launches(events) if wanted is None or launch.get("subagent_type") == wanted)
        return count >= grader.get("min", 1), "%d launch(es)" % count
    if kind == "hook_denied":
        count = deny_count(events)
        return count >= grader.get("min", 1), "%d denial(s)" % count
    if kind == "stub_marker":
        path = os.path.join(project, ".ai-team", "stub-%s.txt" % grader["agent"])
        return os.path.exists(path), path
    if kind == "task_json":
        task = load_task(project)
        if task is None:
            return False, "no task json"
        if grader["path"] == "status":
            value = task.get("status")
            return value == grader["equals"], "status=%s" % value
        if grader["path"] == "ticket_kinds":
            kinds = [t["kind"] for t in task.get("tickets", [])]
            return grader["contains"] in kinds, "tickets=%s" % kinds
        if grader["path"] == "ticket_before_agent":
            # a ticket of this kind must exist AND every Agent launch of the matching type must have
            # happened after the machine had a task -- approximated by: task exists and ticket kind present
            kinds = [t["kind"] for t in task.get("tickets", [])]
            return grader["kind_name"] in kinds, "tickets=%s" % kinds
        return False, "unknown task_json path %s" % grader["path"]
    return False, "unknown grader kind %s" % kind


def run_case(name, variants, model, effort, max_turns, repeat, keep):
    case_dir = os.path.join(CASES_DIR, name)
    with open(os.path.join(case_dir, "case.json")) as handle:
        case = json.load(handle)
    results = {}
    for variant in variants:
        for iteration in range(repeat):
            work, project, head = prepare(case_dir, variant, keep)
            seed(project, case.get("seed", []), head)
            code, events, stderr = run_session(project, case["prompt"], model, effort, max_turns)
            print("\n== %s · %s · run %d/%d · claude exit %d · %d events" % (name, variant, iteration + 1, repeat, code, len(events)))
            if code != 0 and not events:
                print("   claude did not start: %s" % stderr.strip()[-400:])
            for grader in case["graders"]:
                ok, detail = grade(grader, project, events)
                results.setdefault((grader.get("label") or grader["kind"], variant), []).append(ok)
                print("   [%s] %-28s %s" % ("PASS" if ok else "FAIL", grader.get("label") or grader["kind"], detail))
            text = final_text(events).strip().replace("\n", " ")
            if text:
                print("   final text: %s" % text[:300])
            if keep:
                print("   kept: %s" % work)
            else:
                shutil.rmtree(work, ignore_errors=True)
    if set(variants) == {"with", "without"}:
        print("\n-- %s RED/GREEN --" % name)
        for label in {k[0] for k in results}:
            without = all(results.get((label, "without"), [False]))
            with_ = all(results.get((label, "with"), [False]))
            verdict = "RED/GREEN" if (not without and with_) else ("both pass (rule not needed?)" if without and with_ else "not green")
            print("   %-28s without=%s with=%s → %s" % (label, without, with_, verdict))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cases", nargs="*", help="case names under evals/cases/ (default: all)")
    parser.add_argument("--variant", choices=("with", "without", "both"), default="both")
    parser.add_argument("--model", default="haiku")
    parser.add_argument("--effort", default="medium")
    parser.add_argument("--max-turns", type=int, default=40)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--keep", action="store_true", help="keep the temp projects for inspection")
    args = parser.parse_args(argv)
    if shutil.which("claude") is None:
        print("claude is not on PATH", file=sys.stderr)
        return 2
    names = args.cases or sorted(d for d in os.listdir(CASES_DIR) if os.path.isdir(os.path.join(CASES_DIR, d)))
    variants = ["without", "with"] if args.variant == "both" else [args.variant]
    for name in names:
        run_case(name, variants, args.model, args.effort, args.max_turns, args.repeat, args.keep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
