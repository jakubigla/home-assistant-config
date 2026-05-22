# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "pytest"]
# ///
"""Tests for the knowledge layer scripts. Run: uv run --with pytest pytest scripts/knowledge/test_knowledge.py -v"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import _shared


def test_parse_frontmatter_extracts_yaml_and_body():
    text = "---\nsummary: Hello world\nbefore_action:\n  - About to test\n---\n\n# Title\n\nBody.\n"
    fm, body = _shared.parse_frontmatter(text)
    assert fm["summary"] == "Hello world"
    assert fm["before_action"] == ["About to test"]
    assert body.strip().startswith("# Title")


def test_parse_frontmatter_missing_block_raises():
    with pytest.raises(_shared.FrontmatterError):
        _shared.parse_frontmatter("# No frontmatter here\n")


def test_parse_frontmatter_invalid_yaml_raises():
    bad = "---\nsummary: [unclosed\n---\n\nbody\n"
    with pytest.raises(_shared.FrontmatterError):
        _shared.parse_frontmatter(bad)


def test_buckets_constant():
    assert _shared.BUCKETS == ("areas", "integrations", "ops", "tooling")


def _load(name):
    sys.path.insert(0, str(Path(__file__).parent))
    return importlib.import_module(name)


def test_render_leaf_row_with_triggers():
    build = _load("build_index")
    fm = {
        "summary": "Test leaf.",
        "before_action": ["About to do X", "About to do Y"],
        "on_symptom": ["error Z"],
    }
    row = build.render_leaf_row("my-leaf", fm)
    assert "- [my-leaf](my-leaf.md) — Test leaf." in row
    assert "**before**: About to do X; About to do Y" in row
    assert "**symptom**: error Z" in row


def test_render_leaf_row_omits_empty_trigger_lines():
    build = _load("build_index")
    fm = {"summary": "Only before.", "before_action": ["About to do X"]}
    row = build.render_leaf_row("leaf", fm)
    assert "**before**:" in row
    assert "**symptom**:" not in row


def test_splice_between_markers_replaces_content():
    build = _load("build_index")
    original = f"head\n{_shared.LEAVES_START}\nOLD\n{_shared.LEAVES_END}\ntail\n"
    result = build.splice(original, "NEW")
    assert "OLD" not in result
    assert "NEW" in result
    assert result.startswith("head")
    assert result.rstrip().endswith("tail")


def test_build_is_idempotent(tmp_path):
    build = _load("build_index")
    # set up a minimal knowledge tree
    for bucket in _shared.BUCKETS:
        (tmp_path / bucket).mkdir(parents=True)
        (tmp_path / bucket / "INDEX.md").write_text(
            f"# {bucket}/\n\n{_shared.LEAVES_START}\n{_shared.LEAVES_END}\n"
        )
    (tmp_path / "areas" / "sample.md").write_text(
        "---\nsummary: A sample leaf.\nbefore_action:\n  - About to sample\n---\n\n# Sample\n"
    )
    (tmp_path / "INDEX.md").write_text(
        f"# Knowledge\n\n## Scenarios\n\n{_shared.LEAVES_START}\n{_shared.LEAVES_END}\n"
    )
    build.build(tmp_path)
    first = (tmp_path / "areas" / "INDEX.md").read_text()
    build.build(tmp_path)
    second = (tmp_path / "areas" / "INDEX.md").read_text()
    assert first == second
    assert "sample" in first
    assert "About to sample" in first
    root_first = (tmp_path / "INDEX.md").read_text()
    build.build(tmp_path)
    root_second = (tmp_path / "INDEX.md").read_text()
    assert root_first == root_second


def test_render_leaf_row_no_summary_omits_dash():
    build = _load("build_index")
    row = build.render_leaf_row("bare", {"before_action": ["About to x"]})
    assert "- [bare](bare.md)" in row
    assert " — " not in row.splitlines()[0]
