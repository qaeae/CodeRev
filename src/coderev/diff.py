"""Unified diff parsing.

We only care about *added* line numbers on the new side: a finding must point at
a line that the PR actually introduces. Anything else is dropped downstream.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
NEW_FILE_RE = re.compile(r"^\+\+\+ b/(.+)$")


@dataclass
class FileDiff:
    path: str
    added: set[int] = field(default_factory=set)

    def contains(self, line: int) -> bool:
        return line in self.added


def parse_unified_diff(text: str) -> dict[str, FileDiff]:
    """Parse a git diff into {path: FileDiff} keeping only files with added lines."""
    files: dict[str, FileDiff] = {}
    current: FileDiff | None = None
    new_line = 0

    for raw in text.splitlines():
        if raw.startswith("+++ "):
            match = NEW_FILE_RE.match(raw)
            if match:
                path = match.group(1).strip()
                current = files.setdefault(path, FileDiff(path=path))
            else:  # deleted file: +++ /dev/null
                current = None
            continue

        match = HUNK_RE.match(raw)
        if match:
            new_line = int(match.group(1))
            continue

        if current is None:
            continue

        if raw.startswith("+"):
            current.added.add(new_line)
            new_line += 1
        elif raw.startswith(" "):
            new_line += 1
        # '-' lines and '\ No newline' markers do not advance the new side

    return {path: diff for path, diff in files.items() if diff.added}


def diff_stat(files: dict[str, FileDiff]) -> dict[str, int]:
    return {
        "files": len(files),
        "added_lines": sum(len(diff.added) for diff in files.values()),
    }
