"""Markdown containers: a report carries its machine-readable object in exactly ONE
fenced ```json block. The prose around it is never parsed.

An opening fence is a whole line matching `^ {0,3}```json[ \\t]*$` (case sensitive, so
```JSON and ```jsonc open nothing); the block ends at the next whole line of three
backticks. Zero blocks, two or more blocks, or an unclosed fence are structural errors,
never resolved by position ("first wins" and "last wins" both validate a document nobody
wrote).
"""

import json
import re

FENCE_OPEN = re.compile(r"^ {0,3}```json[ \t]*$")
FENCE_CLOSE = re.compile(r"^ {0,3}```[ \t]*$")


def extract_fenced_json(text):
    """Return ((payload, opening_line), None) or (None, "<what is wrong>")."""
    blocks = []
    open_line = None
    content = []
    for number, line in enumerate(text.split("\n"), start=1):
        if open_line is None:
            if FENCE_OPEN.match(line):
                open_line = number
                content = []
        elif FENCE_CLOSE.match(line):
            blocks.append((open_line, content))
            open_line = None
        else:
            content.append(line)
    if open_line is not None:
        return None, (
            "the ```json fence opened at line %d is never closed -- a block ends at a whole "
            "line of three backticks" % open_line
        )
    if not blocks:
        return None, (
            "no fenced ```json block found -- a Markdown container holds the object in exactly "
            "one ```json block (the fence label is case sensitive and must be a whole line)"
        )
    if len(blocks) > 1:
        return None, (
            "expected exactly one fenced ```json block, found %d (fences opened at lines %s)"
            % (len(blocks), ", ".join(str(opened) for opened, _ in blocks))
        )
    opened, content = blocks[0]
    return ("\n".join(content), opened), None


def load_json_block(path):
    """Read a Markdown container and JSON-parse its single block.

    Returns (value, None) or (None, (kind, message)) with kind one of:
      "block-error"  the file does not carry exactly one closed block (a shape violation)
      "json-error"   the block's text is not valid JSON (a shape violation)
      "error"        the file could not be read at all (missing, unreadable, not UTF-8,
                     pathological input) -- what stopped validation from running
    """
    try:
        with open(path, "rb") as handle:
            text = handle.read().decode("utf-8")
    except Exception as exc:  # noqa: BLE001 -- fail closed, never a traceback
        return None, ("error", "%s: %s" % (type(exc).__name__, exc))
    block, problem = extract_fenced_json(text)
    if problem is not None:
        return None, ("block-error", problem)
    payload, fence_line = block
    try:
        return json.loads(payload), None
    except json.JSONDecodeError as exc:
        return None, (
            "json-error",
            "not valid JSON in the fenced ```json block opened at line %d (positions below count "
            "from the first line inside the block): %s" % (fence_line, exc),
        )
    except Exception as exc:  # noqa: BLE001
        return None, ("error", "%s: %s" % (type(exc).__name__, exc))


def render_json_block(value):
    """The canonical way this package writes a block: pretty JSON inside ```json fences."""
    return "```json\n%s\n```\n" % json.dumps(value, indent=2, ensure_ascii=False)
