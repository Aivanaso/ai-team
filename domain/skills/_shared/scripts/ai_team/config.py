"""The project's declared test layout, read from `<root>/.ai-team/config.yaml`.

Two keys only: `strict_tdd` (top level, a boolean) and `structure.test_mirror` (a list of
rules written as block items). The reader is line based -- the machine is stdlib only -- and
ignores every other line. A rule is a source directory prefix, a test directory prefix and
an optional stem prefix and suffix; the extension is kept as it is, so one rule shape serves
every language. The convention is declared in the config, never inferred from the tree.
"""

import os
import re
from typing import NamedTuple, Tuple

from ai_team.store import AI_TEAM_DIR, MachineError

CONFIG_FILE = "config.yaml"
RULE_KEYS = ("source", "tests", "prefix", "suffix")
KEY_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(?:\s+(.*))?$")
NO_RULES_VALUES = ("~", "null", "[]")

MIRROR_BLOCK_TO_ADD = (
    "structure:\n"
    "  test_mirror:\n"
    '    - source: "<source directory>/"\n'
    '      tests: "<mirrored test directory>/"\n'
    '      suffix: "<optional stem suffix>"   # or prefix: "<optional stem prefix>"'
)


class MirrorRule(NamedTuple):
    source: str
    tests: str
    prefix: str
    suffix: str


class ProjectConfig(NamedTuple):
    root: str
    strict_tdd: bool
    mirror_rules: Tuple[MirrorRule, ...]


def _malformed(line_number, problem):
    return MachineError("%s/%s:%d: %s" % (AI_TEAM_DIR, CONFIG_FILE, line_number, problem))


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def _is_content(line):
    stripped = line.strip()
    return bool(stripped) and not stripped.startswith("#")


def _scalar(raw):
    """A value with its trailing comment and one pair of quotes removed."""
    quote = None
    for position, char in enumerate(raw):
        if quote:
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char == "#" and (position == 0 or raw[position - 1] in " \t"):
            raw = raw[:position]
            break
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _directory(value):
    normalized = value[2:] if value.startswith("./") else value
    normalized = normalized.rstrip("/")
    return "" if normalized in ("", ".") else normalized + "/"


def _read_strict_tdd(raw, line_number):
    value = _scalar(raw).lower()
    if value in ("", "~", "null"):
        return False
    if value not in ("true", "false"):
        raise _malformed(line_number, "strict_tdd must be `true` or `false`, found `%s`" % _scalar(raw))
    return value == "true"


def _structure_block(numbered):
    """The (line number, text) pairs nested under the top-level `structure:` key."""
    block, inside = [], False
    for number, line in numbered:
        if _is_content(line) and _indent(line) == 0:
            match = KEY_LINE.match(line)
            inside = bool(match) and match.group(1) == "structure"
            continue
        if inside:
            block.append((number, line))
    return block


def _mirror_body(block):
    """(key line number, inline value, body lines) of `test_mirror`, or None when absent."""
    content = [(n, line) for n, line in block if _is_content(line)]
    if not content:
        return None
    key_indent = _indent(content[0][1])
    for position, (number, line) in enumerate(block):
        if not _is_content(line) or _indent(line) != key_indent:
            continue
        match = KEY_LINE.match(line.strip())
        if not match or match.group(1) != "test_mirror":
            continue
        body = []
        for later_number, later in block[position + 1:]:
            if _is_content(later):
                indent = _indent(later)
                if indent < key_indent or (indent == key_indent and not later.strip().startswith("-")):
                    break
            body.append((later_number, later))
        return number, _scalar(match.group(2) or ""), [(n, l) for n, l in body if _is_content(l)]
    return None


def _rule_from(fields, item_line):
    for key in ("source", "tests"):
        if not fields.get(key, ("",))[0]:
            raise _malformed(fields[key][1] if key in fields else item_line,
                             "test_mirror rule needs a non-empty `%s` directory -- write `%s: \"<directory>/\"`" % (key, key))
    tests = _directory(fields["tests"][0])
    if not tests:
        raise _malformed(fields["tests"][1], "test_mirror `tests` must name a directory below the project root, not the root itself")
    return MirrorRule(
        source=_directory(fields["source"][0]), tests=tests,
        prefix=fields.get("prefix", ("",))[0], suffix=fields.get("suffix", ("",))[0],
    )


def _parse_rules(key_number, inline, body):
    if inline:
        if inline in NO_RULES_VALUES:
            return ()
        raise _malformed(key_number, "test_mirror must be a list: one `- source: ...` item per rule, each followed by its `tests:` line")
    rules, fields, item_line, item_indent = [], None, None, 0
    for number, line in body:
        text = line.strip()
        indent = _indent(line)
        starts_item = text == "-" or text.startswith("- ")
        if starts_item and (fields is None or indent <= item_indent):
            if fields is not None:
                rules.append(_rule_from(fields, item_line))
            fields, item_line, item_indent = {}, number, indent
            text = text[1:].strip()
            if not text:
                continue
        elif fields is None or indent <= item_indent:
            raise _malformed(number, "expected a rule item `- source: \"<directory>/\"`, found `%s`" % text)
        match = KEY_LINE.match(text)
        if not match or match.group(1) not in RULE_KEYS:
            raise _malformed(number, "test_mirror rule lines are `key: value` with key one of %s, found `%s`" % (", ".join(RULE_KEYS), text))
        fields[match.group(1)] = (_scalar(match.group(2) or ""), number)
    if fields is not None:
        rules.append(_rule_from(fields, item_line))
    return tuple(rules)


def parse_config(root, text):
    strict_tdd, rules = False, ()
    numbered = list(enumerate(text.splitlines(), start=1))
    for number, line in numbered:
        match = KEY_LINE.match(line) if _is_content(line) and _indent(line) == 0 else None
        if match and match.group(1) == "strict_tdd":
            strict_tdd = _read_strict_tdd(match.group(2) or "", number)
    body = _mirror_body(_structure_block(numbered))
    if body is not None:
        rules = _parse_rules(*body)
    return ProjectConfig(root=root, strict_tdd=strict_tdd, mirror_rules=rules)


def load_config(root):
    """The declared layout of the project at `root`; a project without config is not strict."""
    path = os.path.join(root, AI_TEAM_DIR, CONFIG_FILE)
    if not os.path.isfile(path):
        return ProjectConfig(root=root, strict_tdd=False, mirror_rules=())
    with open(path, encoding="utf-8") as handle:
        return parse_config(root, handle.read())


def mirror_path(path, rules):
    """The mirror of `path` under the first rule whose source directory holds it, else None.
    A path already inside a rule's test directory is a mirror, not a source."""
    normalized = path[2:] if path.startswith("./") else path
    if any(normalized.startswith(rule.tests) for rule in rules):
        return None
    for rule in rules:
        if normalized.startswith(rule.source):
            directory, name = os.path.split(normalized[len(rule.source):])
            stem, extension = os.path.splitext(name)
            return rule.tests + (directory + "/" if directory else "") + rule.prefix + stem + rule.suffix + extension
    return None


def required_mirror_rules(config):
    """The rules the plan applies: none when the project is not strict; a refusal when it is
    strict and has declared no mirror."""
    if not config.strict_tdd:
        return ()
    if not config.mirror_rules:
        raise MachineError(
            "strict_tdd is true in %s/%s but `structure.test_mirror` declares no rule -- read the project's "
            "test layout once, add these lines to %s/%s (under the existing `structure:` key when there is one), "
            "then re-run the command:\n%s"
            % (AI_TEAM_DIR, CONFIG_FILE, AI_TEAM_DIR, CONFIG_FILE, MIRROR_BLOCK_TO_ADD))
    return config.mirror_rules
