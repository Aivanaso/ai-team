"""`.ai-team/tech-debt.md`: the book of parked findings. Append-only, except the status cell.

Row format (design note §14): date, origin (report + finding id), file:line, severity,
mechanism (the finding's claim), condition (its trigger), status `open | fixed (<hash>)`.
"""

import os

from ai_team.store import atomic_write, read_text, today

HEADER = "| date | origin | file:line | severity | mechanism | condition | status |"
RULE = "|---|---|---|---|---|---|---|"
TITLE = "# Tech Debt Ledger\n\n> Written by the `ai-team` machine (`settle --defer`, `debt fix`). Rows are appended; only the status cell is ever edited.\n"


def _cell(value):
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ").strip() or "-"


def append_findings(path, report_rel, findings):
    rows = []
    for finding in findings:
        rows.append("| %s | %s | %s | %s | %s | %s | open |" % (
            today(),
            _cell("%s %s" % (report_rel, finding.get("id"))),
            _cell("%s:%s" % (finding.get("file"), finding.get("line"))),
            _cell(finding.get("severity")),
            _cell(finding.get("claim")),
            _cell(finding.get("trigger") or "not stated"),
        ))
    if os.path.exists(path):
        text = read_text(path).rstrip("\n")
        lines = text.split("\n")
        table_headers = [i for i, line in enumerate(lines) if line.strip().startswith("| date |")]
        if table_headers and lines[table_headers[-1]].strip() == HEADER:
            text = text + "\n" + "\n".join(rows) + "\n"
        else:
            text = text + "\n\n" + HEADER + "\n" + RULE + "\n" + "\n".join(rows) + "\n"
    else:
        text = TITLE + "\n" + HEADER + "\n" + RULE + "\n" + "\n".join(rows) + "\n"
    atomic_write(path, text)
    return len(rows)


def fix(path, match, commit):
    """Flip the status cell of every open row containing `match` to `fixed (<commit>)`."""
    if not os.path.exists(path):
        return 0
    flipped = 0
    out = []
    for line in read_text(path).split("\n"):
        if line.startswith("|") and match in line and not line.strip().startswith("| date |"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and cells[-1].startswith("open"):
                cells[-1] = "fixed (%s)" % commit
                line = "| " + " | ".join(cells) + " |"
                flipped += 1
        out.append(line)
    if flipped:
        atomic_write(path, "\n".join(out))
    return flipped
