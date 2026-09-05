"""The design file: what the machine reads from `.ai-team/designs/<task>.md`.

Frontmatter (`key: value` lines between `---` fences, no YAML library needed) plus `## `
sections whose names may be Spanish or English (machine.md → "Inputs the machine parses").
Phases are `### Fase N — Title` / `### Phase N — Title` blocks with `Entrega:`/`Delivers:`,
`Escenarios:`/`Scenarios:` bullets and `Check:` commands in backticks.
"""

import re

from ai_team.store import MachineError, atomic_write, read_text, utc_now

SECTION_ALIASES = {
    "objective": ("objetivo", "objective"),
    "context": ("contexto", "context"),
    "questions": ("preguntas y respuestas", "questions and answers"),
    "approaches": ("enfoques considerados", "approaches considered"),
    "design": ("diseño", "diseno", "design"),
    "decisions": ("decisiones", "decisions"),
    "security": ("seguridad", "security"),
    "out_of_scope": ("fuera de alcance", "out of scope"),
    "phases": ("fases", "phases"),
}
SUBSECTION_ALIASES = {
    "surfaces": ("superficies nombradas", "named surfaces"),
    "external_conditions": ("condiciones externas a conservar", "external conditions to preserve"),
}
PHASE_HEADER = re.compile(r"^###\s+(?:Fase|Phase)\s+(\d+)\s*(?:[—–:-]+\s*)?(.*?)\s*$", re.IGNORECASE)
PHASE_KEY = re.compile(r"^\s*(?:[-*]\s+)?\**(Entrega|Delivers|Escenarios|Scenarios|Checks?|Comprobaci[oó]n)\**\s*:\s*(.*)$", re.IGNORECASE)
BULLET = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+(.*)$")
BACKTICKED = re.compile(r"`([^`]+)`")
PATH_TOKEN = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./\\-]*")
NOT_APPLICABLE = re.compile(r"^\s*(no aplica|not applicable|n/a)\b", re.IGNORECASE)
NEW_MARK = re.compile(r"\((nueva|nuevo|new)\)", re.IGNORECASE)


def _canonical(name, aliases):
    lowered = name.strip().lower().rstrip(":")
    for key, names in aliases.items():
        if lowered in names:
            return key
    return None


def _unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if value in ("", "null", "~"):
        return None
    return value


def parse_frontmatter(text):
    """Return (fields, body). No frontmatter → ({}, text)."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text
    fields = {}
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return fields, "\n".join(lines[index + 1:])
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", lines[index])
        if match:
            fields[match.group(1)] = _unquote(re.sub(r"\s+#.*$", "", match.group(2)))
    return {}, text


def set_frontmatter(path, updates):
    """Rewrite frontmatter keys in place (add the missing ones); the body is untouched."""
    text = read_text(path)
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise MachineError("%s has no frontmatter to update" % path)
    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end is None:
        raise MachineError("%s has an unterminated frontmatter" % path)
    pending = dict(updates)
    for index in range(1, end):
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:", lines[index])
        if match and match.group(1) in pending:
            lines[index] = '%s: "%s"' % (match.group(1), pending.pop(match.group(1)))
    for key, value in pending.items():
        lines.insert(end, '%s: "%s"' % (key, value))
        end += 1
    atomic_write(path, "\n".join(lines))


def bullets(lines):
    """Bullet items (`- `, `* `, `1. `) with indented continuation lines folded in."""
    items = []
    for line in lines:
        match = BULLET.match(line)
        if match:
            items.append(match.group(1).strip())
        elif items and line.startswith((" ", "\t")) and line.strip():
            items[-1] += " " + line.strip()
    return items


def _split_sections(body):
    sections = {}
    order = []
    current = None
    for line in body.split("\n"):
        if line.startswith("## ") and not line.startswith("### "):
            key = _canonical(line[3:], SECTION_ALIASES) or line[3:].strip().lower()
            current = key
            sections.setdefault(current, [])
            order.append(current)
            continue
        if current is not None:
            sections[current].append(line)
    return sections


def _subsections(lines):
    subs = {}
    current = None
    for line in lines:
        if line.startswith("### "):
            current = _canonical(line[4:], SUBSECTION_ALIASES) or line[4:].strip().lower()
            subs.setdefault(current, [])
            continue
        if current is not None:
            subs[current].append(line)
    return subs


def _prose(lines):
    return "\n".join(line for line in lines).strip()


def _surface_paths(items):
    """`src/foo.php:42 — why` → {"action": "MODIFY", "path": "src/foo.php", "evidence": "src/foo.php:42"}."""
    surfaces = []
    for item in items:
        text = item.replace("`", "")
        token = None
        for candidate in PATH_TOKEN.findall(text):
            if "/" in candidate or "." in candidate:
                token = candidate
                break
        if token is None:
            continue
        path = token.rstrip(".,;")
        line_match = re.search(re.escape(path) + r":(\d+)", text)
        evidence = "%s:%s" % (path, line_match.group(1)) if line_match else "new"
        action = "CREATE" if NEW_MARK.search(text) or evidence == "new" else "MODIFY"
        surfaces.append({"action": action, "path": path, "evidence": evidence})
    return surfaces


def _parse_phases(lines):
    phases = []
    current = None
    mode = None
    for line in lines:
        header = PHASE_HEADER.match(line)
        if header:
            current = {"n": int(header.group(1)), "title": header.group(2).strip() or "phase %s" % header.group(1),
                       "delivers": "", "scenarios": [], "checks": []}
            phases.append(current)
            mode = None
            continue
        if current is None:
            continue
        key = PHASE_KEY.match(line)
        if key:
            name = key.group(1).lower()
            rest = key.group(2).strip()
            if name in ("entrega", "delivers"):
                mode = "delivers"
                current["delivers"] = rest
            elif name in ("escenarios", "scenarios"):
                mode = "scenarios"
                if rest:
                    current["scenarios"].append(rest)
            else:
                mode = "checks"
                current["checks"].extend(BACKTICKED.findall(rest) or ([rest] if rest else []))
            continue
        if mode == "delivers" and line.strip():
            current["delivers"] = (current["delivers"] + " " + line.strip()).strip()
        elif mode == "scenarios":
            match = BULLET.match(line)
            if match:
                current["scenarios"].append(match.group(1).strip())
            elif current["scenarios"] and line.startswith((" ", "\t")) and line.strip():
                current["scenarios"][-1] += " " + line.strip()
        elif mode == "checks" and line.strip():
            commands = BACKTICKED.findall(line)
            if commands:
                current["checks"].extend(commands)
            else:
                match = BULLET.match(line)
                if match:
                    current["checks"].append(match.group(1).strip())
    return phases


def load_design(path):
    """Parse a design file into a plain dict. Raises MachineError when unreadable."""
    try:
        text = read_text(path)
    except OSError as exc:
        raise MachineError("design file %s cannot be read: %s" % (path, exc), 2)
    fields, body = parse_frontmatter(text)
    sections = _split_sections(body)
    design_sub = _subsections(sections.get("design", []))
    security_lines = sections.get("security", [])
    security_items = bullets(security_lines)
    if NOT_APPLICABLE.match(_prose(security_lines)):
        security_items = []
    return {
        "path": path,
        "title": fields.get("title"),
        "status": fields.get("status"),
        "security": fields.get("security"),
        "map_report": fields.get("map_report"),
        "created_at": fields.get("created_at"),
        "approved_at": fields.get("approved_at"),
        "objective": _prose(sections.get("objective", [])),
        "decisions": bullets(sections.get("decisions", [])),
        "security_measures": security_items,
        "out_of_scope": bullets(sections.get("out_of_scope", [])),
        "surfaces": _surface_paths(bullets(design_sub.get("surfaces", []))),
        "external_conditions": bullets(design_sub.get("external_conditions", [])),
        "phases": _parse_phases(sections.get("phases", [])),
    }


def design_problems(design, require_approved=True):
    """What keeps this design from generating a plan. Empty list = usable."""
    problems = []
    if require_approved and design["status"] != "approved":
        problems.append("design status is %r -- the user's yes flips it: `ai-team design approve <path>`" % design["status"])
    if design["security"] == "pending":
        problems.append("design says security: pending -- settle the threat-model first, or set security: not-needed with a reason")
    if not design["objective"]:
        problems.append("## Objetivo / ## Objective is empty")
    if not design["decisions"]:
        problems.append("## Decisiones / ## Decisions has no bullet -- a plan without invariants has no constraints")
    if not design["phases"]:
        problems.append("## Fases / ## Phases has no `### Fase N — Title` block")
    for index, phase in enumerate(design["phases"], start=1):
        if phase["n"] != index:
            problems.append("phase headers must number 1..N in order (got %d at position %d)" % (phase["n"], index))
        if not phase["scenarios"]:
            problems.append("phase %d has no Escenarios/Scenarios bullets" % phase["n"])
        if not phase["checks"]:
            problems.append("phase %d has no Check: command in backticks" % phase["n"])
    return problems


def approve(path):
    design = load_design(path)
    if design["status"] == "approved":
        raise MachineError("design %s is already approved" % path)
    if design["security"] == "pending":
        raise MachineError(
            "design %s says security: pending -- the threat-model's measures enter as decisions BEFORE approval "
            "(settle the security-threat-model ticket), or set security: not-needed with a reason" % path
        )
    problems = design_problems(design, require_approved=False)
    if problems:
        raise MachineError("design %s is not complete:\n  - %s" % (path, "\n  - ".join(problems)))
    set_frontmatter(path, {"status": "approved", "approved_at": utc_now()})
    return load_design(path)
