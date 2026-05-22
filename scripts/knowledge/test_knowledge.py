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


def _seed_tree(tmp_path):
    for bucket in _shared.BUCKETS:
        (tmp_path / bucket).mkdir(parents=True)
        (tmp_path / bucket / "INDEX.md").write_text(
            f"# {bucket}/\n\n{_shared.LEAVES_START}\n{_shared.LEAVES_END}\n"
        )
    (tmp_path / "INDEX.md").write_text(
        f"# Knowledge\n\n## Scenarios\n\n{_shared.LEAVES_START}\n{_shared.LEAVES_END}\n"
    )


def test_check_passes_clean_tree(tmp_path):
    check = _load("check_index")
    build = _load("build_index")
    _seed_tree(tmp_path)
    (tmp_path / "ops" / "good.md").write_text(
        "---\nsummary: A good leaf.\nbefore_action:\n  - About to deploy\n---\n\n# Good\n"
    )
    build.build(tmp_path)
    errors = check.check(tmp_path, claude_root=tmp_path / "nonexistent")
    assert errors == []


def test_check_flags_long_summary(tmp_path):
    check = _load("check_index")
    build = _load("build_index")
    _seed_tree(tmp_path)
    long = "x" * 130
    (tmp_path / "ops" / "bad.md").write_text(
        f"---\nsummary: {long}\nbefore_action:\n  - About to deploy\n---\n\n# Bad\n"
    )
    build.build(tmp_path)
    errors = check.check(tmp_path, claude_root=tmp_path / "nonexistent")
    assert any("summary" in e for e in errors)


def test_check_flags_no_triggers(tmp_path):
    check = _load("check_index")
    build = _load("build_index")
    _seed_tree(tmp_path)
    (tmp_path / "ops" / "bad.md").write_text(
        "---\nsummary: No triggers here.\n---\n\n# Bad\n"
    )
    build.build(tmp_path)
    errors = check.check(tmp_path, claude_root=tmp_path / "nonexistent")
    assert any("trigger" in e for e in errors)


def test_check_flags_trigger_with_embedded_path(tmp_path):
    check = _load("check_index")
    build = _load("build_index")
    _seed_tree(tmp_path)
    (tmp_path / "ops" / "bad.md").write_text(
        "---\nsummary: Coupled trigger.\nbefore_action:\n  - See ops/other.md\n---\n\n# Bad\n"
    )
    build.build(tmp_path)
    errors = check.check(tmp_path, claude_root=tmp_path / "nonexistent")
    assert any("path" in e.lower() for e in errors)


def test_check_flags_index_drift(tmp_path):
    check = _load("check_index")
    build = _load("build_index")
    _seed_tree(tmp_path)
    (tmp_path / "ops" / "good.md").write_text(
        "---\nsummary: A leaf.\nbefore_action:\n  - About to deploy\n---\n\n# Good\n"
    )
    build.build(tmp_path)
    # hand-corrupt a bucket INDEX
    (tmp_path / "ops" / "INDEX.md").write_text(
        f"# ops/\n\n{_shared.LEAVES_START}\nDRIFT\n{_shared.LEAVES_END}\n"
    )
    errors = check.check(tmp_path, claude_root=tmp_path / "nonexistent")
    assert any("drift" in e.lower() or "stale" in e.lower() for e in errors)


def test_check_flags_dangling_scenario_ref(tmp_path):
    check = _load("check_index")
    build = _load("build_index")
    _seed_tree(tmp_path)
    build.build(tmp_path)
    root = tmp_path / "INDEX.md"
    txt = root.read_text().replace(
        "## Scenarios\n",
        "## Scenarios\n\n### X\nLoad: `ops/ghost.md`.\n",
    )
    root.write_text(txt)
    errors = check.check(tmp_path, claude_root=tmp_path / "nonexistent")
    assert any("ghost" in e for e in errors)


def test_check_flags_dangling_skill_pointer(tmp_path):
    check = _load("check_index")
    build = _load("build_index")
    _seed_tree(tmp_path)
    build.build(tmp_path)
    claude = tmp_path / "claude"
    skill_dir = claude / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "open `knowledge/INDEX.md` and pick the **ghost-leaf** leaf."
    )
    errors = check.check(tmp_path, claude_root=claude)
    assert any("ghost-leaf" in e for e in errors)


def test_check_flags_root_index_drift(tmp_path):
    check = _load("check_index")
    build = _load("build_index")
    _seed_tree(tmp_path)
    build.build(tmp_path)
    # corrupt the root index between markers
    root = tmp_path / "INDEX.md"
    txt = root.read_text()
    txt = txt.replace(f"{_shared.LEAVES_START}\n", f"{_shared.LEAVES_START}\nROOTDRIFT\n")
    root.write_text(txt)
    errors = check.check(tmp_path, claude_root=tmp_path / "nonexistent")
    assert any("stale" in e.lower() or "drift" in e.lower() for e in errors)


def test_check_invalid_frontmatter_does_not_crash(tmp_path):
    check = _load("check_index")
    build = _load("build_index")
    _seed_tree(tmp_path)
    build.build(tmp_path)
    # leaf with broken YAML — build() would raise if drift ran on it
    (tmp_path / "ops" / "broken.md").write_text("---\nsummary: [unclosed\n---\n\nbody\n")
    errors = check.check(tmp_path, claude_root=tmp_path / "nonexistent")
    assert any("ops/broken.md" in e for e in errors)


def test_check_allows_nonbucket_slash_in_trigger(tmp_path):
    check = _load("check_index")
    build = _load("build_index")
    _seed_tree(tmp_path)
    (tmp_path / "ops" / "ok.md").write_text(
        "---\nsummary: Fine.\nbefore_action:\n  - About to edit config/setup.md by hand\n---\n\n# OK\n"
    )
    build.build(tmp_path)
    errors = check.check(tmp_path, claude_root=tmp_path / "nonexistent")
    assert errors == []
