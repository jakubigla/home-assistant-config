"""Shared helpers for the knowledge layer scripts (frontmatter, constants, paths)."""

from __future__ import annotations

from pathlib import Path

import yaml

LEAVES_START = "<!-- LEAVES:START -->"
LEAVES_END = "<!-- LEAVES:END -->"
SUMMARY_MAX = 120
BODY_SOFT_CAP = 70  # lines
LINE_WIDTH_MAX = 100  # chars — hard-wrap body source so the line count stays honest


class FrontmatterError(ValueError):
    """Raised when a leaf has missing or invalid frontmatter."""


def repo_root() -> Path:
    """Repo root = two levels above this file (scripts/knowledge/_shared.py)."""
    return Path(__file__).resolve().parent.parent.parent


def knowledge_root() -> Path:
    return repo_root() / "knowledge"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split a leaf into (frontmatter dict, body). Raises FrontmatterError if absent."""
    if not text.startswith("---"):
        raise FrontmatterError("missing opening --- frontmatter fence")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise FrontmatterError("missing closing --- frontmatter fence")
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        raise FrontmatterError(f"invalid YAML in frontmatter: {exc}") from exc
    if not isinstance(fm, dict):
        raise FrontmatterError("frontmatter is not a mapping")
    return fm, parts[2]


def buckets(knowledge: Path) -> list[str]:
    """Discover bucket names = every subdirectory of knowledge/ (sorted).

    Buckets are not a fixed set — they're whatever groupings exist on disk, so
    an author can create a new one by adding a leaf under a new directory.
    """
    if not knowledge.is_dir():
        return []
    return sorted(p.name for p in knowledge.iterdir() if p.is_dir())


def iter_leaves(knowledge: Path) -> dict[str, list[Path]]:
    """Map each discovered bucket -> sorted list of leaf paths (excludes INDEX.md)."""
    result: dict[str, list[Path]] = {}
    for bucket in buckets(knowledge):
        leaves = sorted(
            p for p in (knowledge / bucket).glob("*.md") if p.name != "INDEX.md"
        )
        result[bucket] = leaves
    return result
