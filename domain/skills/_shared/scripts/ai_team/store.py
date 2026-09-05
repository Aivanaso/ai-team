"""Where the machine keeps its state: one JSON per task under <root>/.ai-team/tasks/."""

import datetime
import json
import os
import re
import shutil
import tempfile

AI_TEAM_DIR = ".ai-team"
TASKS_SUBDIR = "tasks"
DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}-")
SCHEMA = 1


def launcher():
    """How to invoke the machine from a shell: `ai-team` when on PATH, else the launcher's path."""
    if shutil.which("ai-team"):
        return "ai-team"
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ai-team")


class MachineError(Exception):
    """A refused verb or unusable input; the CLI prints str(exc) and exits with .code."""

    def __init__(self, message, code=1):
        super().__init__(message)
        self.code = code


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def find_root(start):
    """Walk up from `start` to the nearest directory containing .ai-team/. None if absent."""
    current = os.path.realpath(start)
    while True:
        if os.path.isdir(os.path.join(current, AI_TEAM_DIR)):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def atomic_write(path, text):
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=directory, prefix=".ai-team-", suffix=".tmp", delete=False
    )
    try:
        with handle:
            handle.write(text)
        os.replace(handle.name, path)
    except BaseException:
        if os.path.exists(handle.name):
            os.unlink(handle.name)
        raise


def read_text(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


class Store:
    def __init__(self, root):
        self.root = os.path.realpath(root)
        self.ai_team = os.path.join(self.root, AI_TEAM_DIR)
        self.tasks_dir = os.path.join(self.ai_team, TASKS_SUBDIR)

    # --- paths -------------------------------------------------------------------
    def rel(self, path):
        """Repo-relative form of a path (absolute or already relative)."""
        if os.path.isabs(path):
            return os.path.relpath(os.path.realpath(path), self.root)
        return os.path.normpath(path)

    def abs(self, rel_path):
        return os.path.join(self.root, rel_path)

    def contained(self, rel_path):
        """True when rel_path resolves inside the project root."""
        target = os.path.realpath(self.abs(rel_path))
        try:
            return os.path.commonpath([self.root, target]) == self.root
        except ValueError:
            return False

    def task_path(self, task_id):
        return os.path.join(self.tasks_dir, task_id + ".json")

    # --- tasks -------------------------------------------------------------------
    def list_tasks(self):
        if not os.path.isdir(self.tasks_dir):
            return []
        tasks = []
        for name in sorted(os.listdir(self.tasks_dir)):
            if name.endswith(".json"):
                tasks.append(self.load(name[:-5]))
        return tasks

    def load(self, task_id):
        path = self.task_path(task_id)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except FileNotFoundError:
            raise MachineError("no task %r under %s" % (task_id, self.rel(self.tasks_dir)), 2)
        except ValueError as exc:
            raise MachineError("task file %s is not valid JSON: %s" % (self.rel(path), exc), 2)
        if not isinstance(data, dict) or data.get("task") != task_id:
            raise MachineError("task file %s does not describe task %r" % (self.rel(path), task_id), 2)
        return data

    def save(self, task):
        task["updated_at"] = utc_now()
        atomic_write(self.task_path(task["task"]), json.dumps(task, indent=2, ensure_ascii=False) + "\n")

    def current(self):
        """The one active task, or None. Two active tasks is a corrupted store."""
        active = [t for t in self.list_tasks() if t.get("status") == "active"]
        if len(active) > 1:
            raise MachineError(
                "more than one active task (%s) -- pause all but one with `ai-team pause`"
                % ", ".join(t["task"] for t in active), 2
            )
        return active[0] if active else None

    def paused(self):
        return [t for t in self.list_tasks() if t.get("status") == "paused"]

    def new_task(self, slug, kind, design=None):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", slug or ""):
            raise MachineError("slug must be letters, digits, '.', '_' or '-' (got %r)" % slug, 2)
        task_id = slug if DATE_PREFIX.match(slug) else "%s-%s" % (today(), slug)
        if os.path.exists(self.task_path(task_id)):
            raise MachineError("task %s already exists" % task_id)
        current = self.current()
        if current is not None:
            raise MachineError(
                "task %s is still active -- `ai-team close` it (or `ai-team pause`) before opening another"
                % current["task"]
            )
        now = utc_now()
        task = {
            "schema": SCHEMA,
            "task": task_id,
            "kind": kind,
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "closed_at": None,
            "design": design,
            "plan": None,
            "scope_report": None,
            "scope_skipped": None,
            "pending_question": None,
            "phases": [],
            "tickets": [],
            "rulings": [],
        }
        self.save(task)
        return task
