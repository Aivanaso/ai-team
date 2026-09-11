"""The working tree as one hash. `fingerprint` writes the whole tree -- tracked changes and
untracked files alike, minus what the project ignores -- into a throwaway index and returns
its git tree id, so two moments of the tree compare as two strings and, when they differ,
`changed_between` names the paths. Nothing touches the project's own index."""

import os
import subprocess
import tempfile


def _git(root, args, env=None):
    return subprocess.run(["git", "-C", root] + args, capture_output=True, text=True, check=False, env=env)


def fingerprint(root):
    """The tree id of the working tree, or None when the repository cannot say (no commit yet,
    not a git repository)."""
    handle, index = tempfile.mkstemp(prefix="ai-team-index-")
    os.close(handle)
    os.unlink(index)  # git creates the index itself; an empty existing file is a corrupt one
    env = dict(os.environ, GIT_INDEX_FILE=index)
    try:
        if _git(root, ["read-tree", "HEAD"], env).returncode != 0:
            return None
        if _git(root, ["add", "-A"], env).returncode != 0:
            return None
        # .ai-team/ is the machine's own ledger, written between two settles: never part of the tree
        # (dropped from the throwaway index afterwards -- naming an ignored path in a pathspec makes git exit 1)
        if _git(root, ["rm", "-r", "-q", "--cached", "--ignore-unmatch", "--", ".ai-team"], env).returncode != 0:
            return None
        written = _git(root, ["write-tree"], env)
        return written.stdout.strip() or None if written.returncode == 0 else None
    finally:
        if os.path.exists(index):
            os.unlink(index)


def changed_between(root, old_tree, new_tree):
    """`STATUS<TAB>path` lines between two tree ids; empty when git cannot compare them."""
    diff = _git(root, ["diff-tree", "-r", "--name-status", old_tree, new_tree])
    if diff.returncode != 0:
        return []
    return [line for line in diff.stdout.splitlines() if line.strip()]


def restore_commands(old_tree, changed):
    """One shell line per changed path that puts the working tree back to `old_tree` -- the
    blobs are in the object database because `fingerprint` wrote them."""
    commands = []
    for line in changed:
        status, _, path = line.partition("\t")
        if status.startswith("A"):
            commands.append("rm -- '%s'" % path)
        else:
            commands.append("git cat-file blob %s:'%s' > '%s'" % (old_tree, path, path))
    return commands
