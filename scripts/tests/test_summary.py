"""`ai-team summary [--last N]`: what the recorded tasks of a project add up to. The verb reads
the task JSONs and prints; a figure the JSON does not hold is shown as `not recorded`, never
added as zero, and the tokens and duration of a resumed implementer stay out of every mean and total."""

import json
import os

import helpers
from helpers import ProjectCase


def ticket(ticket_id, kind, outcome="ok", phase=None, attempt=None, **figures):
    """A settled ticket as the machine records it; `figures` override tokens / duration_s / tool_uses,
    and a figure passed as `...` (Ellipsis) leaves the key out of the JSON altogether."""
    entry = {
        "id": ticket_id, "kind": kind, "phase": phase, "attempt": attempt,
        "issued_at": "2026-11-10T10:00:00Z", "settled_at": "2026-11-10T10:05:00Z", "outcome": outcome,
        "model": "sonnet", "tokens": 1000, "tool_uses": 10, "duration_s": 60,
        "report": None, "verdict": None, "findings": None, "deferred": [], "tree": None,
    }
    entry.update(figures)
    return {key: value for key, value in entry.items() if value is not Ellipsis}


def phase(n, attempts, title="a phase"):
    return {"n": n, "title": title, "status": "committed", "attempts": attempts, "tier": 1,
            "tier_reason": "tier 1: test", "commit": "abc", "amendments": []}


def task_json(task_id, tickets=(), phases=(), kind="bounded", status="done", created_at=None):
    return {"schema": 1, "task": task_id, "kind": kind, "status": status,
            "created_at": created_at or task_id[:10] + "T09:00:00Z", "updated_at": "2026-11-10T11:00:00Z",
            "closed_at": None, "design": None, "plan": None, "scope_report": None, "scope_skipped": None,
            "pending_question": None, "phases": list(phases), "tickets": list(tickets), "rulings": []}


class SummaryCase(ProjectCase):
    def record(self, *tasks):
        for task in tasks:
            self.write(".ai-team/tasks/%s.json" % task["task"], json.dumps(task, indent=2) + "\n")

    def summary(self, *args):
        _, out, _ = self.ai("summary", *args)
        return out

    def line_of(self, out, start):
        return next(line for line in out.splitlines() if line.strip().startswith(start))


class SummaryOfAnEmptyProject(SummaryCase):
    def test_a_project_with_no_recorded_task_prints_one_line_and_exits_zero(self):
        code, out, _ = self.ai("summary")
        self.assertEqual(code, 0)
        self.assertEqual(len(out.strip().splitlines()), 1)
        self.assertIn("no recorded task", out)

    def test_an_empty_tasks_directory_says_the_same(self):
        os.makedirs(os.path.join(self.root, ".ai-team", "tasks"))
        code, out, _ = self.ai("summary")
        self.assertEqual(code, 0)
        self.assertIn("no recorded task", out)

    def test_last_must_be_a_positive_integer(self):
        self.record(task_json("2026-11-01-a"))
        _, _, err = self.ai("summary", "--last", "0", expect=2)
        self.assertIn("--last", err)


class SummaryOfTheTicketKinds(SummaryCase):
    def setUp(self):
        super().setUp()
        self.record(task_json("2026-11-01-first", tickets=[
            ticket("t1", "implementer", phase=1, attempt=1, tokens=1000, duration_s=100),
            ticket("t2", "reviewer", outcome="ok", phase=1, attempt=1, tokens=300, duration_s=30),
            ticket("t3", "implementer", outcome="blocked", phase=2, attempt=1, tokens=3000, duration_s=200),
            ticket("t4", "reviewer", outcome="ok", phase=2, attempt=1, tokens=500, duration_s=50),
            {**ticket("t5", "reviewer", phase=2, attempt=2), "settled_at": None, "outcome": None},
        ]))

    def test_each_kind_shows_how_many_tickets_settled_and_with_which_outcomes(self):
        out = self.summary()
        implementer = self.line_of(out, "implementer")
        self.assertIn("2", implementer)
        self.assertIn("ok 1", implementer)
        self.assertIn("blocked 1", implementer)
        reviewer = self.line_of(out, "reviewer")
        self.assertIn("ok 2", reviewer)

    def test_an_open_ticket_is_not_counted(self):
        reviewer = self.line_of(self.summary(), "reviewer")
        self.assertEqual(reviewer.split()[1], "2")

    def test_each_kind_shows_the_mean_and_total_of_its_duration_and_tokens(self):
        implementer = self.line_of(self.summary(), "implementer")
        self.assertIn("mean 150s", implementer)
        self.assertIn("total 300s", implementer)
        self.assertIn("mean 2000", implementer)
        self.assertIn("total 4000", implementer)

    def test_the_kind_with_the_most_outcomes_other_than_ok_comes_last(self):
        out = self.summary().strip().splitlines()[-1]
        self.assertIn("other than ok", out)
        self.assertIn("implementer", out)
        self.assertNotIn("reviewer", out)

    def test_a_tie_names_every_kind_in_it(self):
        out = self.summary().strip().splitlines()[-1]
        self.assertNotIn("reviewer", out)
        self.record(task_json("2026-11-02-second", tickets=[ticket("t1", "reviewer", outcome="blocked", phase=1, attempt=1)]))
        out = self.summary().strip().splitlines()[-1]
        self.assertIn("implementer", out)
        self.assertIn("reviewer", out)

    def test_a_warning_is_an_outcome_other_than_ok(self):
        self.record(task_json("2026-11-02-second", tickets=[
            ticket("t1", "scout-map", outcome="warning"), ticket("t2", "scout-map", outcome="warning"),
            ticket("t3", "scout-map", outcome="warning"),
        ]))
        self.assertIn("scout-map", self.summary().strip().splitlines()[-1])

    def test_when_every_ticket_ended_ok_the_last_line_says_so(self):
        for name in os.listdir(os.path.join(self.root, ".ai-team", "tasks")):
            os.unlink(os.path.join(self.root, ".ai-team", "tasks", name))
        self.record(task_json("2026-11-03-clean", tickets=[ticket("t1", "implementer", phase=1, attempt=1)]))
        last = self.summary().strip().splitlines()[-1]
        self.assertIn("no outcome other than ok", last)


class SummaryOfAResumedImplementer(SummaryCase):
    def setUp(self):
        super().setUp()
        self.record(task_json("2026-11-01-resumed", tickets=[
            ticket("t1", "implementer", outcome="blocked", phase=1, attempt=1, tokens=1000, duration_s=100),
            ticket("t2", "implementer", outcome="blocked", phase=1, attempt=2, tokens=7777, duration_s=6543),
            ticket("t3", "implementer", outcome="ok", phase=1, attempt=3, tokens=9999, duration_s=8765),
            ticket("t4", "reviewer", phase=1, attempt=3, tokens=400),
        ], phases=[phase(1, 3)]))
        self.out = self.summary()

    def test_resumed_tokens_stay_out_of_the_mean_and_the_total_of_the_kind(self):
        implementer = self.line_of(self.out, "implementer")
        self.assertIn("mean 1000", implementer)
        self.assertIn("total 1000", implementer)
        self.assertNotIn("7777", implementer)
        self.assertNotIn("9999", implementer)

    def test_resumed_durations_stay_out_of_the_mean_and_the_total_of_the_kind(self):
        implementer = self.line_of(self.out, "implementer")
        self.assertIn("mean 100s", implementer)
        self.assertIn("total 100s", implementer)
        self.assertNotIn("6543", implementer)
        self.assertNotIn("8765", implementer)

    def test_resumed_tokens_and_durations_are_listed_apart_and_labelled_cumulative(self):
        resumed = self.line_of(self.out, "resumed implementer")
        self.assertIn("cumulative", resumed)
        for figure in ("7777", "9999", "6543s", "8765s"):
            self.assertIn(figure, resumed)

    def test_the_resumed_tickets_still_count_as_settled_tickets_with_their_outcome(self):
        implementer = self.line_of(self.out, "implementer")
        self.assertEqual(implementer.split()[1], "3")
        self.assertIn("blocked 2", implementer)

    def test_no_figure_adds_resumed_tokens_to_the_others(self):
        for added in ("17776", "18776", "8888", "9259", "15408", "15308", "7654", "5136"):
            self.assertNotIn(added, self.out)

    def test_a_fresh_attempt_after_the_resumed_ones_is_a_fresh_ticket(self):
        self.record(task_json("2026-11-02-fresh-again", tickets=[
            ticket("t1", "implementer", outcome="blocked", phase=1, attempt=4, tokens=50),
            ticket("t2", "implementer", outcome="ok", phase=1, attempt=5, tokens=3000),
        ]))
        implementer = self.line_of(self.summary(), "implementer")
        self.assertIn("total 4000", implementer)


class SummaryOfMissingFigures(SummaryCase):
    def test_a_kind_whose_tickets_hold_no_figure_shows_not_recorded(self):
        self.record(task_json("2026-11-01-dead", tickets=[
            ticket("t1", "scout-map", outcome="infra-death", tokens=None, duration_s=None, tool_uses=None),
            ticket("t2", "scout-map", outcome="infra-death", tokens=...),
        ]))
        line = self.line_of(self.summary(), "scout-map")
        self.assertIn("not recorded", line)
        self.assertNotIn("mean 0", line)
        self.assertNotIn("total 0", line)

    def test_a_null_figure_and_an_absent_key_never_add_as_zero(self):
        self.record(task_json("2026-11-01-mixed", tickets=[
            ticket("t1", "reviewer", phase=1, attempt=1, tokens=900, duration_s=90),
            ticket("t2", "reviewer", outcome="infra-death", phase=1, attempt=1, tokens=None, duration_s=None),
            ticket("t3", "reviewer", phase=1, attempt=1, tokens=..., duration_s=...),
        ]))
        line = self.line_of(self.summary(), "reviewer")
        self.assertIn("mean 900", line)
        self.assertIn("total 900", line)
        self.assertIn("mean 90s", line)
        self.assertIn("1 of 3 recorded", line)
        self.assertNotIn("mean 300", line)

    def test_a_resumed_ticket_without_tokens_is_listed_as_not_recorded(self):
        self.record(task_json("2026-11-01-resumed-dead", tickets=[
            ticket("t1", "implementer", phase=1, attempt=1, tokens=500),
            ticket("t2", "implementer", outcome="infra-death", phase=1, attempt=2, tokens=None),
        ]))
        resumed = self.line_of(self.summary(), "resumed implementer")
        self.assertIn("not recorded", resumed)

    def test_a_resumed_ticket_without_duration_is_listed_as_not_recorded(self):
        self.record(task_json("2026-11-01-resumed-no-duration", tickets=[
            ticket("t1", "implementer", phase=1, attempt=1, duration_s=100),
            ticket("t2", "implementer", phase=1, attempt=2, tokens=800, duration_s=None),
        ]))
        resumed = self.line_of(self.summary(), "resumed implementer")
        self.assertIn("duration not recorded", resumed)
        self.assertIn("tokens 800", resumed)

    def test_a_phase_without_its_attempts_figure_shows_not_recorded(self):
        broken = phase(1, 1)
        del broken["attempts"]
        self.record(task_json("2026-11-01-no-attempts", phases=[broken]))
        self.assertIn("attempts not recorded", self.summary())


class SummaryOfTheTasks(SummaryCase):
    def test_each_task_lists_the_attempts_of_each_of_its_phases(self):
        self.record(task_json("2026-11-01-two-phases", kind="large", phases=[phase(1, 1, "first"), phase(2, 3, "second")]))
        out = self.summary()
        self.assertIn("2026-11-01-two-phases", out)
        self.assertIn("phase 1", self.line_of(out, "phase 1"))
        self.assertIn("1 attempt", self.line_of(out, "phase 1"))
        self.assertIn("3 attempts", self.line_of(out, "phase 2"))

    def test_a_task_without_phases_says_nothing_was_planned(self):
        self.record(task_json("2026-11-01-unplanned", status="active"))
        self.assertIn("no phase planned", self.summary())

    def test_last_keeps_the_most_recent_tasks_only(self):
        self.record(task_json("2026-11-01-oldest"), task_json("2026-11-02-middle"), task_json("2026-11-03-newest"))
        out = self.summary("--last", "2")
        self.assertNotIn("2026-11-01-oldest", out)
        self.assertIn("2026-11-02-middle", out)
        self.assertIn("2026-11-03-newest", out)

    def test_last_leaves_the_tickets_of_the_older_tasks_out_of_the_kind_table(self):
        self.record(
            task_json("2026-11-01-oldest", tickets=[ticket("t1", "retro", tokens=111)]),
            task_json("2026-11-03-newest", tickets=[ticket("t1", "scout-map", tokens=222)]),
        )
        out = self.summary("--last", "1")
        self.assertIn("scout-map", out)
        self.assertNotIn("retro", out)

    def test_without_last_every_task_is_summarized(self):
        self.record(task_json("2026-11-01-oldest"), task_json("2026-11-03-newest"))
        out = self.summary()
        self.assertIn("2026-11-01-oldest", out)
        self.assertIn("2026-11-03-newest", out)

    def test_a_last_larger_than_the_recorded_tasks_shows_them_all(self):
        self.record(task_json("2026-11-01-only"))
        self.assertIn("2026-11-01-only", self.summary("--last", "9"))


class SummaryOnlyReads(SummaryCase):
    def snapshot(self):
        contents = {}
        for folder, _, names in os.walk(os.path.join(self.root, ".ai-team")):
            for name in names:
                path = os.path.join(folder, name)
                with open(path, "rb") as handle:
                    contents[path] = handle.read()
        return contents

    def test_no_file_under_ai_team_changes(self):
        self.record(
            task_json("2026-11-01-a", tickets=[ticket("t1", "implementer", phase=1, attempt=1)], phases=[phase(1, 1)]),
            task_json("2026-11-02-b", tickets=[ticket("t1", "reviewer", outcome="failed", tokens=None)], status="active"),
        )
        self.write(".ai-team/tech-debt.md", "| row |\n")
        before = self.snapshot()
        self.ai("summary")
        self.ai("summary", "--last", "1")
        self.assertEqual(self.snapshot(), before)

    def test_it_creates_nothing_in_a_project_with_no_task(self):
        before = self.snapshot()
        self.ai("summary")
        self.assertEqual(self.snapshot(), before)


class SummaryIsDocumented(SummaryCase):
    def test_machine_md_has_a_verbs_table_row_for_it(self):
        path = os.path.join(helpers.SCRIPTS, "..", "machine.md")
        with open(path, encoding="utf-8") as handle:
            rows = [line for line in handle.read().splitlines() if line.startswith("| `summary")]
        self.assertEqual(len(rows), 1)
        self.assertIn("--last", rows[0])
        self.assertIn("not recorded", rows[0])
