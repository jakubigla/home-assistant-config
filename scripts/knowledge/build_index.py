#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Regenerate knowledge/INDEX.md as a single flat table of every leaf, from frontmatter.

One row per leaf across all buckets: Leaf (linked) | Summary | Triggers.
Bucket lives in the leaf's link path, not a column. No per-bucket INDEX files,
no scenarios. Deterministic: output is a pure function of leaf frontmatter.

Run: uv run scripts/knowledge/build_index.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import _shared


def _escape(text: str) -> str:
    """Escape characters that would break a markdown table cell."""
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _triggers_cell(fm: dict) -> str:
    """One <br>-separated line per trigger, each prefixed before:/symptom:.

    <br> renders as a line break in markdown viewers (readable) while staying a
    plain-text delimiter for the routing model — cleaner than semicolon-joining.
    """
    lines = [f"**before:** {_escape(str(b))}" for b in (fm.get("before_action") or [])]
    lines += [f"**symptom:** {_escape(str(s))}" for s in (fm.get("on_symptom") or [])]
    return "<br>".join(lines)


def render_row(bucket: str, leaf: Path) -> str:
    fm, _ = _shared.parse_frontmatter(leaf.read_text(encoding="utf-8"))
    name = leaf.stem
    link = f"[{name}]({bucket}/{name}.md)"
    summary = _escape(fm.get("summary", ""))
    return f"| {link} | {summary} | {_triggers_cell(fm)} |"


def render_table(knowledge: Path) -> str:
    rows = [
        render_row(bucket, leaf)
        for bucket, leaves in _shared.iter_leaves(knowledge).items()
        for leaf in leaves
    ]
    header = "| Leaf | Summary | Triggers |\n|---|---|---|"
    return header + "\n" + "\n".join(rows) if rows else header


def splice(text: str, new_inner: str) -> str:
    """Replace content between LEAVES markers with new_inner."""
    start = text.index(_shared.LEAVES_START) + len(_shared.LEAVES_START)
    end = text.index(_shared.LEAVES_END)
    if end < start:
        raise ValueError("LEAVES:END appears before LEAVES:START")
    return text[:start] + "\n" + new_inner + "\n" + text[end:]


def render_index(knowledge: Path) -> tuple[Path, str]:
    """Compute expected root INDEX.md content WITHOUT writing. Returns (path, text)."""
    root_path = knowledge / "INDEX.md"
    if root_path.exists():
        base = root_path.read_text(encoding="utf-8")
    else:
        base = f"# Knowledge\n\n{_shared.LEAVES_START}\n{_shared.LEAVES_END}\n"
    return root_path, splice(base, render_table(knowledge))


def build(knowledge: Path) -> None:
    """Regenerate the root INDEX.md leaf table."""
    path, text = render_index(knowledge)
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    build(_shared.knowledge_root())
    print("knowledge index rebuilt")
