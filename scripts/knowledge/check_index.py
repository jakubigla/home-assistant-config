#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Validate the knowledge layer: frontmatter schema, INDEX drift, scenario refs, skill pointers.

Run: uv run scripts/knowledge/check_index.py
Exits nonzero on any fatal error. Body-length issues print as warnings only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import _shared
import build_index

POINTER_RE = re.compile(r"pick(?:ing)? (?:the )?\*\*([^*]+)\*\* leaf")
SCENARIO_REF_RE = re.compile(r"`([a-z]+/[a-z0-9-]+\.md)`")
PATH_IN_TRIGGER_RE = re.compile(r"(?:areas|integrations|ops|tooling)/[a-z0-9-]+\.md")


def _check_frontmatter(knowledge: Path) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Validates schema + trigger decoupling + body length."""
    errors: list[str] = []
    warnings: list[str] = []
    for bucket, leaves in _shared.iter_leaves(knowledge).items():
        for leaf in leaves:
            rel = f"{bucket}/{leaf.name}"
            try:
                fm, body = _shared.parse_frontmatter(leaf.read_text(encoding="utf-8"))
            except _shared.FrontmatterError as exc:
                errors.append(f"{rel}: {exc}")
                continue
            summary = (fm.get("summary") or "").strip()
            if not summary:
                errors.append(f"{rel}: missing summary")
            elif len(summary) > _shared.SUMMARY_MAX:
                errors.append(
                    f"{rel}: summary {len(summary)} chars exceeds {_shared.SUMMARY_MAX}"
                )
            triggers = (fm.get("before_action") or []) + (fm.get("on_symptom") or [])
            if not triggers:
                errors.append(f"{rel}: needs at least one before_action or on_symptom trigger")
            for t in triggers:
                if PATH_IN_TRIGGER_RE.search(str(t)):
                    errors.append(f"{rel}: trigger embeds a leaf path (decouple): {t!r}")
            body_lines = len(body.strip().splitlines())
            if body_lines > _shared.BODY_SOFT_CAP:
                warnings.append(
                    f"{rel}: body {body_lines} lines exceeds soft-cap {_shared.BODY_SOFT_CAP}"
                )
    return errors, warnings


def _check_drift(knowledge: Path) -> list[str]:
    """Compare on-disk INDEX files against freshly rendered content (no writes)."""
    if not (knowledge / "INDEX.md").exists():
        return ["knowledge/INDEX.md missing"]
    errors: list[str] = []
    for path, expected in build_index.render_all(knowledge).items():
        if not path.exists():
            errors.append(f"{path.name} missing — run `just knowledge-index`")
        elif path.read_text(encoding="utf-8") != expected:
            rel = path.relative_to(knowledge)
            errors.append(f"{rel} stale — run `just knowledge-index` (drift)")
    return errors


def _check_scenarios(knowledge: Path) -> list[str]:
    errors: list[str] = []
    root = knowledge / "INDEX.md"
    if not root.exists():
        return ["knowledge/INDEX.md missing"]
    full = root.read_text(encoding="utf-8").split(_shared.LEAVES_START)[0]
    text = full.split("## Scenarios", 1)[1] if "## Scenarios" in full else ""
    for ref in SCENARIO_REF_RE.findall(text):
        if not (knowledge / ref).exists():
            errors.append(f"scenario references missing leaf: {ref}")
    return errors


def _check_skill_pointers(knowledge: Path, claude_root: Path) -> list[str]:
    errors: list[str] = []
    skills_dir = claude_root / "skills"
    if not skills_dir.exists():
        return errors
    known = {leaf.stem for leaves in _shared.iter_leaves(knowledge).values() for leaf in leaves}
    for skill_md in skills_dir.rglob("*.md"):
        for name in POINTER_RE.findall(skill_md.read_text(encoding="utf-8")):
            stripped = name.strip()
            if "/" in stripped or "." in stripped:
                continue  # not a bare leaf-name pointer; skip
            if stripped not in known:
                errors.append(
                    f"{skill_md.relative_to(claude_root)}: dangling pointer to **{name}** leaf"
                )
    return errors


def check(knowledge: Path, *, claude_root: Path | None = None) -> list[str]:
    """Run every fatal check; return aggregated error messages. Warnings print to stderr."""
    if claude_root is None:
        claude_root = _shared.repo_root() / ".claude"
    errors: list[str] = []
    fm_errors, warnings = _check_frontmatter(knowledge)
    errors += fm_errors
    # Drift requires a clean build; skip if frontmatter is broken (build would raise).
    if not fm_errors:
        errors += _check_drift(knowledge)
    errors += _check_scenarios(knowledge)
    errors += _check_skill_pointers(knowledge, claude_root)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    return errors


if __name__ == "__main__":
    found = check(_shared.knowledge_root())
    if found:
        for e in found:
            print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
    print("knowledge layer OK")
