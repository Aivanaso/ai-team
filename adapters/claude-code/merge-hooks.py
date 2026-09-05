#!/usr/bin/env python3
"""merge-hooks.py -- register (or remove) the ai-team machine hooks inside a
user-owned Claude Code settings.json, without disturbing anything else in it.

    python3 merge-hooks.py <settings.json> <hooks.json> [--remove]

`~/.claude/settings.json` belongs to the operator, not to this framework: it
carries their own Stop/Notification handlers, their permission allow-list, the
status line, the model choice. So the merge is subtractive-then-additive and
identifies ai-team's own handlers by ONE substring -- `_shared/scripts/ai-team` in a
handler's `command`:

  1. copy the existing file to <settings.json>.bak-<UTC YYYYmmddTHHMMSSZ>
     (before parsing, so even the malformed-input error can name a copy); if
     that name is taken -- two runs inside one second -- `-2`, `-3`, ... is
     appended, because a backup that overwrites an earlier backup destroys the
     very snapshot someone would reach for;
  2. drop every handler, under any event and any matcher, whose command
     contains `_shared/scripts/ai-team`; a matcher group our removal emptied is
     dropped too, and so is an event list our removal emptied -- a group or
     list that was ALREADY empty is foreign data and stays;
  3. unless --remove, append the template's own entries for each event it
     declares;
  4. write back with json.dump(indent=2, ensure_ascii=False) + a trailing
     newline, atomically: a NamedTemporaryFile in the target's own directory,
     then os.replace. The target is os.path.realpath(settings.json), so a
     settings.json symlinked into a dotfiles checkout keeps its symlink and the
     file it points at is what gets replaced.

Everything else -- every key, every foreign hook, every entry's field order --
survives verbatim, because the document is round-tripped through json.load /
json.dump rather than edited textually. Running it twice yields a
byte-identical settings.json (step 2 undoes step 3 before redoing it), which
is what makes it safe to call from an installer that the operator re-runs
after every `git pull`.

`disableAllHooks` is never written: it would kill the operator's own hooks,
and this tool's whole contract is that it touches only its own handlers.

Exit codes: 0 merged (or nothing to remove), 1 the settings file could not be
read as a JSON object, or the template could not be read -- one message on
stderr naming the backup, never a traceback.
"""

import copy
import datetime
import json
import os
import shutil
import sys
import tempfile

MARKER = "_shared/scripts/ai-team"


def _fail(message):
    sys.stderr.write("merge-hooks: %s\n" % message)
    sys.exit(1)


def _backup(path):
    """Copy an existing settings file aside. Returns the copy's path or None.

    A backup NEVER overwrites an earlier one: two runs in the same second (an
    installer re-run, a script loop) would otherwise leave one snapshot where
    there should be two, and the older -- the one from before any ai-team
    change -- is exactly the one that would be lost.
    """
    if not os.path.isfile(path):
        return None
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = "%s.bak-%s" % (path, stamp)
    suffix = 1
    while os.path.exists(destination):
        suffix += 1
        destination = "%s.bak-%s-%d" % (path, stamp, suffix)
    shutil.copy2(path, destination)
    return destination


def _load_json_object(path, label, backup):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except ValueError as exc:
        hint = " (a copy is at %s)" % backup if backup else ""
        _fail("%s %s is not valid JSON: %s -- left unchanged%s" % (label, path, exc, hint))
    except OSError as exc:
        _fail("%s %s could not be read: %s" % (label, path, exc))
    if not isinstance(data, dict):
        hint = " (a copy is at %s)" % backup if backup else ""
        _fail("%s %s is not a JSON object -- left unchanged%s" % (label, path, hint))
    return data


def _is_ours(handler):
    return (
        isinstance(handler, dict)
        and isinstance(handler.get("command"), str)
        and MARKER in handler["command"]
    )


def _strip_our_handlers(hooks):
    """Remove ai-team handlers in place. Returns how many were removed."""
    removed = 0
    for event in list(hooks.keys()):
        groups = hooks[event]
        if not isinstance(groups, list):
            continue  # foreign shape: never rewritten
        kept_groups = []
        event_removed = 0
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                kept_groups.append(group)
                continue
            handlers = group["hooks"]
            kept = [handler for handler in handlers if not _is_ours(handler)]
            event_removed += len(handlers) - len(kept)
            if not kept and len(handlers) != len(kept):
                # Our removal emptied this matcher group -- drop the group.
                continue
            group["hooks"] = kept
            kept_groups.append(group)
        removed += event_removed
        if not kept_groups and event_removed:
            # Our removal emptied this event -- drop the key so a --remove run
            # restores the document's foreign-only shape byte for byte.
            del hooks[event]
        else:
            hooks[event] = kept_groups
    return removed


def _write(path, data):
    """Replace the file settings.json RESOLVES to, never the symlink itself.

    A settings.json symlinked into a dotfiles checkout is the common case on a
    managed machine; replacing the link with a regular file silently detaches
    the operator's configuration from version control.
    """
    target = os.path.realpath(path)
    directory = os.path.dirname(target) or "."
    os.makedirs(directory, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=directory, prefix=".merge-hooks-", suffix=".json",
        delete=False,
    )
    try:
        with handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        if os.path.exists(target):
            shutil.copymode(target, handle.name)
        os.replace(handle.name, target)
    except BaseException:
        if os.path.exists(handle.name):
            os.unlink(handle.name)
        raise


def main(argv):
    arguments = [item for item in argv if item != "--remove"]
    remove = "--remove" in argv
    if len(arguments) != 2:
        _fail("usage: merge-hooks.py <settings.json> <hooks.json> [--remove]")
    settings_path, template_path = arguments

    backup = _backup(settings_path)

    if os.path.isfile(settings_path):
        settings = _load_json_object(settings_path, "settings file", backup)
    elif remove:
        print("merge-hooks: %s does not exist -- nothing to remove" % settings_path)
        return 0
    else:
        settings = {}

    hooks = settings.get("hooks", {})
    if not isinstance(hooks, dict):
        hint = " (a copy is at %s)" % backup if backup else ""
        _fail(
            "settings file %s has a `hooks` key that is not an object -- left unchanged%s"
            % (settings_path, hint)
        )

    removed = _strip_our_handlers(hooks)

    added = 0
    if not remove:
        template = _load_json_object(template_path, "hooks template", None)
        template_hooks = template.get("hooks")
        if not isinstance(template_hooks, dict):
            _fail("hooks template %s carries no `hooks` object" % template_path)
        for event, groups in template_hooks.items():
            if not isinstance(groups, list):
                _fail("hooks template %s: `hooks.%s` is not a list" % (template_path, event))
            existing = hooks.setdefault(event, [])
            if not isinstance(existing, list):
                hint = " (a copy is at %s)" % backup if backup else ""
                _fail(
                    "settings file %s: `hooks.%s` is not a list -- left unchanged%s"
                    % (settings_path, event, hint)
                )
            for group in groups:
                existing.append(copy.deepcopy(group))
                added += 1

    if hooks:
        settings["hooks"] = hooks
    elif "hooks" in settings and removed:
        # Our own removal emptied it; a settings file that never had the key
        # does not gain an empty one.
        del settings["hooks"]

    _write(settings_path, settings)
    print(
        "merge-hooks: %s -- %d ai-team handler group(s) registered, %d removed%s"
        % (
            settings_path,
            added,
            removed,
            " (backup: %s)" % backup if backup else " (created)",
        )
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 -- never a traceback in an installer
        _fail("%s: %s" % (type(exc).__name__, str(exc).split("\n")[0]))
