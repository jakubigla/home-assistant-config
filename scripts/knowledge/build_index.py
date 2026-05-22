#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Regenerate knowledge/<bucket>/INDEX.md + the root INDEX.md bucket pointers from leaf frontmatter.

Run: uv run scripts/knowledge/build_index.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import _shared


def render_leaf_row(name: str, fm: dict) -> str:
    """Render one leaf's INDEX block: link line + before/symptom trigger lines."""
    summary = fm.get("summary", "").strip()
    suffix = f" — {summary}" if summary else ""
    lines = [f"- [{name}]({name}.md){suffix}"]
    before = fm.get("before_action") or []
    symptom = fm.get("on_symptom") or []
    if before:
        lines.append(f"  - **before**: {'; '.join(before)}")
    if symptom:
        lines.append(f"  - **symptom**: {'; '.join(symptom)}")
    return "\n".join(lines)


def splice(text: str, new_inner: str) -> str:
    """Replace content between LEAVES markers with new_inner."""
    start = text.index(_shared.LEAVES_START) + len(_shared.LEAVES_START)
    end = text.index(_shared.LEAVES_END)
    if end < start:
        raise ValueError("LEAVES:END appears before LEAVES:START")
    return text[:start] + "\n" + new_inner + "\n" + text[end:]


def _render_bucket(leaves: list[Path]) -> str:
    rows = []
    for leaf in leaves:
        fm, _ = _shared.parse_frontmatter(leaf.read_text(encoding="utf-8"))
        rows.append(render_leaf_row(leaf.stem, fm))
    return "\n".join(rows) if rows else ""


def render_all(knowledge: Path) -> dict[Path, str]:
    """Compute expected INDEX.md contents WITHOUT writing. Maps path -> expected text.

    Mirrors build(): each bucket INDEX spliced with its leaf rows, root INDEX
    spliced with bucket pointers. A bucket/root INDEX that doesn't yet exist on
    disk is rendered from the skeleton build() would create.
    """
    expected: dict[Path, str] = {}
    all_leaves = _shared.iter_leaves(knowledge)
    for bucket, leaves in all_leaves.items():
        index_path = knowledge / bucket / "INDEX.md"
        if index_path.exists():
            base = index_path.read_text(encoding="utf-8")
        else:
            base = f"# {bucket}/\n\n{_shared.LEAVES_START}\n{_shared.LEAVES_END}\n"
        inner = _render_bucket(leaves)
        expected[index_path] = splice(base, inner)

    root_path = knowledge / "INDEX.md"
    pointers = "\n".join(
        f"### {bucket}/\nSee `{bucket}/INDEX.md`." for bucket in _shared.BUCKETS
    )
    if root_path.exists():
        expected[root_path] = splice(root_path.read_text(encoding="utf-8"), pointers)
    return expected


def build(knowledge: Path) -> None:
    """Regenerate every bucket INDEX.md + the root INDEX.md bucket-pointer section."""
    for path, text in render_all(knowledge).items():
        path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    build(_shared.knowledge_root())
    print("knowledge indexes rebuilt")
