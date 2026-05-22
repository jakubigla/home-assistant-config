# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "pytest"]
# ///
"""Tests for the knowledge layer scripts. Run: uv run --with pytest pytest scripts/knowledge/test_knowledge.py -v"""

from __future__ import annotations

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
