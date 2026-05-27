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


def test_buckets_discovered_from_dirs(tmp_path):
    (tmp_path / "ops").mkdir()
    (tmp_path / "zebra").mkdir()
    (tmp_path / "INDEX.md").write_text("x")  # file, not a dir — ignored
    assert _shared.buckets(tmp_path) == ["ops", "zebra"]


def test_buckets_empty_when_no_dirs(tmp_path):
    assert _shared.buckets(tmp_path) == []


def _load(name):
    # sys.path already includes this dir (module-level insert above).
    return importlib.import_module(name)


def test_triggers_cell_merges_before_and_symptom():
    build = _load("build_index")
    fm = {
        "summary": "Test leaf.",
        "before_action": ["About to do X", "About to do Y"],
        "on_symptom": ["error Z"],
    }
    assert build._triggers_cell(fm) == (
        "**before:** About to do X<br>**before:** About to do Y<br>**symptom:** error Z"
    )


def test_render_row_reads_file(tmp_path):
    build = _load("build_index")
    leaf = tmp_path / "my-leaf.md"
    leaf.write_text(
        "---\nsummary: Test leaf.\nbefore_action:\n  - About to do X\n---\n\n# Body\n"
    )
    row = build.render_row("ops", leaf)
    assert row.startswith("| [my-leaf](ops/my-leaf.md) | Test leaf. | **before:** About to do X |")


def test_triggers_cell_omits_empty_groups():
    build = _load("build_index")
    assert build._triggers_cell({"before_action": ["About to X"]}) == "**before:** About to X"
    assert build._triggers_cell({"on_symptom": ["boom"]}) == "**symptom:** boom"


def test_escape_neutralizes_pipe_and_newline():
    build = _load("build_index")
    assert build._escape("a | b\nc") == "a \\| b c"


def test_splice_between_markers_replaces_content():
    build = _load("build_index")
    original = f"head\n{_shared.LEAVES_START}\nOLD\n{_shared.LEAVES_END}\ntail\n"
    result = build.splice(original, "NEW")
    assert "OLD" not in result
    assert "NEW" in result
    assert result.startswith("head")
    assert result.rstrip().endswith("tail")


def _seed_tree(tmp_path, *bucket_dirs):
    """Seed a knowledge root: an empty INDEX plus any bucket dirs the test writes into.

    Buckets are discovered from dirs, so a test only needs the ones it uses;
    default to the two the suite writes leaves into.
    """
    for bucket in bucket_dirs or ("ops", "areas"):
        (tmp_path / bucket).mkdir(parents=True, exist_ok=True)
    (tmp_path / "INDEX.md").write_text(
        f"# Knowledge\n\n{_shared.LEAVES_START}\n{_shared.LEAVES_END}\n"
    )


def test_build_is_idempotent_and_includes_leaf(tmp_path):
    build = _load("build_index")
    _seed_tree(tmp_path)
    (tmp_path / "areas" / "sample.md").write_text(
        "---\nsummary: A sample leaf.\nbefore_action:\n  - About to sample\n---\n\n# Sample\n"
    )
    build.build(tmp_path)
    first = (tmp_path / "INDEX.md").read_text()
    build.build(tmp_path)
    second = (tmp_path / "INDEX.md").read_text()
    assert first == second
    assert "| Leaf | Summary | Triggers |" in first
    assert "[sample](areas/sample.md)" in first
    assert "About to sample" in first


def test_build_renders_header_only_when_no_leaves(tmp_path):
    build = _load("build_index")
    _seed_tree(tmp_path)
    build.build(tmp_path)
    text = (tmp_path / "INDEX.md").read_text()
    assert "| Leaf | Summary | Triggers |" in text


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
    # hand-corrupt the single root INDEX
    root = tmp_path / "INDEX.md"
    txt = root.read_text().replace(f"{_shared.LEAVES_START}\n", f"{_shared.LEAVES_START}\nDRIFT\n")
    root.write_text(txt)
    errors = check.check(tmp_path, claude_root=tmp_path / "nonexistent")
    assert any("drift" in e.lower() or "stale" in e.lower() for e in errors)


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


def test_rebuild_and_stage_clean_returns_zero(tmp_path, monkeypatch):
    rs = _load("rebuild_and_stage")
    build = _load("build_index")
    _seed_tree(tmp_path)
    (tmp_path / "ops" / "good.md").write_text(
        "---\nsummary: A leaf.\nbefore_action:\n  - About to deploy\n---\n\n# Good\n"
    )
    build.build(tmp_path)  # INDEX already fresh
    monkeypatch.setattr(rs._shared, "knowledge_root", lambda: tmp_path)
    assert rs.main() == 0


def test_rebuild_and_stage_drift_rewrites_and_returns_one(tmp_path, monkeypatch):
    rs = _load("rebuild_and_stage")
    _seed_tree(tmp_path)
    (tmp_path / "ops" / "good.md").write_text(
        "---\nsummary: A leaf.\nbefore_action:\n  - About to deploy\n---\n\n# Good\n"
    )
    # INDEX never built → stale vs frontmatter.
    monkeypatch.setattr(rs._shared, "knowledge_root", lambda: tmp_path)
    monkeypatch.setattr(rs.subprocess, "run", lambda *a, **k: None)  # stub git add
    assert rs.main() == 1
    assert "[good](ops/good.md)" in (tmp_path / "INDEX.md").read_text()
