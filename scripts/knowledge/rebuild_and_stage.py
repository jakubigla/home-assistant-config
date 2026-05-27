#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Pre-commit: regenerate knowledge/INDEX.md from frontmatter, re-stage if it changed.

Deterministic — INDEX.md is a pure function of leaf frontmatter, so it should never
be hand-edited or allowed to drift. This rebuilds it and, if the rebuild changed the
file, `git add`s the result and exits nonzero (standard pre-commit auto-fix pattern:
the hook fails once so the regenerated file lands staged; re-running then passes).

Run: uv run scripts/knowledge/rebuild_and_stage.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import _shared
import build_index


def main() -> int:
    knowledge = _shared.knowledge_root()
    path, expected = build_index.render_index(knowledge)
    before = path.read_text(encoding="utf-8") if path.exists() else None
    if before == expected:
        return 0
    path.write_text(expected, encoding="utf-8")
    subprocess.run(["git", "add", str(path)], check=True)
    try:
        shown = path.relative_to(_shared.repo_root())
    except ValueError:
        shown = path
    print(f"rebuilt + staged {shown} (was stale)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
