# Knowledge Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a frontmatter-routed knowledge layer to home-assistant-config — small markdown "leaves" discovered by intent, kept fresh by generated indexes, validated on commit, bracketed by router (recall) and author (write) skills.

**Architecture:** Leaves live under four buckets in `knowledge/`. Each leaf carries YAML frontmatter (`summary`, `before_action[]`, `on_symptom[]`). Two PEP 723 `uv` scripts generate bucket/root INDEXes from frontmatter and validate them. A pre-commit hook + `just` recipes wire it in. Two Claude skills (`knowledge-router`, `knowledge-author`) drive recall and write.

**Tech Stack:** Python 3.11+ (PEP 723 inline-metadata `uv` scripts, PyYAML), `just`, pre-commit, Markdown.

---

## File Structure

| Path | Responsibility |
|---|---|
| `scripts/knowledge/build_index.py` | Regenerate bucket + root `INDEX.md` from leaf frontmatter |
| `scripts/knowledge/check_index.py` | Validate frontmatter schema, INDEX drift, scenario refs, skill pointers |
| `scripts/knowledge/_shared.py` | Shared frontmatter parser + bucket/marker constants (imported by both) |
| `knowledge/INDEX.md` | Hand-edited scenarios + generated bucket pointers |
| `knowledge/{areas,integrations,ops,tooling}/INDEX.md` | Generated leaf directory per bucket |
| `knowledge/{bucket}/*.md` | Individual leaves |
| `justfile` | Add `knowledge-index`, `knowledge-check` recipes |
| `.pre-commit-config.yaml` | Add local `knowledge-index` validation hook |
| `CLAUDE.md` | Add `## Knowledge layer` section + continuous-improvement bullet |
| `.claude/skills/knowledge-router/SKILL.md` | Recall skill |
| `.claude/skills/knowledge-author/SKILL.md` | Write skill |

**Note on `_shared.py`:** PEP 723 scripts can't import a sibling module that has its own inline-metadata block. `_shared.py` is a plain module (no shebang, no `# /// script` block); `build_index.py` and `check_index.py` import it via `sys.path` insertion of their own dir. Both scripts declare `pyyaml` in their own metadata.

---

## Task 1: Shared frontmatter module + scaffold directories

**Files:**
- Create: `scripts/knowledge/_shared.py`
- Create: `knowledge/areas/.gitkeep`, `knowledge/integrations/.gitkeep`, `knowledge/ops/.gitkeep`, `knowledge/tooling/.gitkeep`
- Test: `scripts/knowledge/test_knowledge.py`

- [ ] **Step 1: Create bucket directories with .gitkeep**

```bash
mkdir -p knowledge/areas knowledge/integrations knowledge/ops knowledge/tooling
touch knowledge/areas/.gitkeep knowledge/integrations/.gitkeep knowledge/ops/.gitkeep knowledge/tooling/.gitkeep
```

- [ ] **Step 2: Write the failing test**

Create `scripts/knowledge/test_knowledge.py`:

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "pytest"]
# ///
"""Tests for the knowledge layer scripts. Run: uv run --with pytest pytest scripts/knowledge/test_knowledge.py -v"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import _shared


def test_parse_frontmatter_extracts_yaml_and_body():
    text = "---\nsummary: Hello world\nbefore_action:\n  - About to test\n---\n\n# Title\n\nBody.\n"
    fm, body = _shared.parse_frontmatter(text)
    assert fm["summary"] == "Hello world"
    assert fm["before_action"] == ["About to test"]
    assert body.strip().startswith("# Title")


def test_parse_frontmatter_missing_block_raises():
    import pytest
    with pytest.raises(_shared.FrontmatterError):
        _shared.parse_frontmatter("# No frontmatter here\n")


def test_buckets_constant():
    assert _shared.BUCKETS == ("areas", "integrations", "ops", "tooling")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run --with pytest pytest scripts/knowledge/test_knowledge.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named '_shared'`

- [ ] **Step 4: Write `_shared.py`**

Create `scripts/knowledge/_shared.py` (plain module — no shebang, no inline metadata):

```python
"""Shared helpers for the knowledge layer scripts (frontmatter, constants, paths)."""

from __future__ import annotations

from pathlib import Path

import yaml

BUCKETS: tuple[str, ...] = ("areas", "integrations", "ops", "tooling")
LEAVES_START = "<!-- LEAVES:START -->"
LEAVES_END = "<!-- LEAVES:END -->"
SUMMARY_MAX = 120
BODY_SOFT_CAP = 70


class FrontmatterError(ValueError):
    """Raised when a leaf has no parseable YAML frontmatter block."""


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
    fm = yaml.safe_load(parts[1]) or {}
    if not isinstance(fm, dict):
        raise FrontmatterError("frontmatter is not a mapping")
    return fm, parts[2]


def iter_leaves(knowledge: Path) -> dict[str, list[Path]]:
    """Map each bucket name -> sorted list of leaf paths (excludes INDEX.md, dotfiles)."""
    result: dict[str, list[Path]] = {}
    for bucket in BUCKETS:
        bucket_dir = knowledge / bucket
        leaves = sorted(
            p
            for p in bucket_dir.glob("*.md")
            if p.name != "INDEX.md"
        )
        result[bucket] = leaves
    return result
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run --with pytest pytest scripts/knowledge/test_knowledge.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add scripts/knowledge/_shared.py scripts/knowledge/test_knowledge.py knowledge/
git commit -m "feat(knowledge): shared frontmatter module + bucket scaffold"
```

---

## Task 2: Index generator (`build_index.py`)

**Files:**
- Create: `scripts/knowledge/build_index.py`
- Create: `knowledge/INDEX.md` (initial scenarios skeleton + markers)
- Modify: `scripts/knowledge/test_knowledge.py` (add generator tests)

- [ ] **Step 1: Create root INDEX skeleton**

Create `knowledge/INDEX.md`:

```markdown
# Knowledge

Frontmatter-routed how-to layer. Leaves live under `areas/`, `integrations/`, `ops/`, `tooling/`.
The `knowledge-router` skill routes intent here; `knowledge-author` writes leaves.

## Scenarios

<!-- LEAVES:START -->
<!-- LEAVES:END -->
```

(Scenarios get filled in Task 5; bucket pointers regenerate between the markers.)

- [ ] **Step 2: Write failing generator tests**

Append to `scripts/knowledge/test_knowledge.py`:

```python
import importlib


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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run --with pytest pytest scripts/knowledge/test_knowledge.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'build_index'`

- [ ] **Step 4: Write `build_index.py`**

Create `scripts/knowledge/build_index.py`:

```python
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
    lines = [f"- [{name}]({name}.md) — {summary}"]
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
    return text[:start] + "\n" + new_inner + "\n" + text[end:]


def _render_bucket(knowledge: Path, bucket: str, leaves: list[Path]) -> str:
    rows = []
    for leaf in leaves:
        fm, _ = _shared.parse_frontmatter(leaf.read_text())
        rows.append(render_leaf_row(leaf.stem, fm))
    return "\n".join(rows) if rows else ""


def build(knowledge: Path) -> None:
    """Regenerate every bucket INDEX.md + the root INDEX.md bucket-pointer section."""
    all_leaves = _shared.iter_leaves(knowledge)
    for bucket, leaves in all_leaves.items():
        index_path = knowledge / bucket / "INDEX.md"
        if not index_path.exists():
            index_path.write_text(
                f"# {bucket}/\n\n{_shared.LEAVES_START}\n{_shared.LEAVES_END}\n"
            )
        inner = _render_bucket(knowledge, bucket, leaves)
        index_path.write_text(splice(index_path.read_text(), inner))

    # root pointers
    root_path = knowledge / "INDEX.md"
    pointers = "\n".join(
        f"### {bucket}/\nSee `{bucket}/INDEX.md`." for bucket in _shared.BUCKETS
    )
    root_path.write_text(splice(root_path.read_text(), pointers))


if __name__ == "__main__":
    build(_shared.knowledge_root())
    print("knowledge indexes rebuilt")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run --with pytest pytest scripts/knowledge/test_knowledge.py -v`
Expected: PASS (all)

- [ ] **Step 6: Run generator against real tree**

Run: `uv run scripts/knowledge/build_index.py`
Expected: prints `knowledge indexes rebuilt`; creates the four bucket `INDEX.md` files (empty leaf sections) and fills root pointers.

- [ ] **Step 7: Commit**

```bash
git add scripts/knowledge/build_index.py scripts/knowledge/test_knowledge.py knowledge/
git commit -m "feat(knowledge): index generator from leaf frontmatter"
```

---

## Task 3: Validator (`check_index.py`)

**Files:**
- Create: `scripts/knowledge/check_index.py`
- Modify: `scripts/knowledge/test_knowledge.py` (add validator tests)

- [ ] **Step 1: Write failing validator tests**

Append to `scripts/knowledge/test_knowledge.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest pytest scripts/knowledge/test_knowledge.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'check_index'`

- [ ] **Step 3: Write `check_index.py`**

Create `scripts/knowledge/check_index.py`:

```python
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
PATH_IN_TRIGGER_RE = re.compile(r"[a-z]+/[a-z0-9-]+\.md")


def _check_frontmatter(knowledge: Path) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Validates schema + trigger decoupling + body length."""
    errors: list[str] = []
    warnings: list[str] = []
    for bucket, leaves in _shared.iter_leaves(knowledge).items():
        for leaf in leaves:
            rel = f"{bucket}/{leaf.name}"
            try:
                fm, body = _shared.parse_frontmatter(leaf.read_text())
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
    """Generate INDEXes into memory, compare to disk."""
    errors: list[str] = []
    on_disk = {
        bucket: (knowledge / bucket / "INDEX.md").read_text()
        for bucket in _shared.BUCKETS
        if (knowledge / bucket / "INDEX.md").exists()
    }
    root_disk = (knowledge / "INDEX.md").read_text() if (knowledge / "INDEX.md").exists() else None
    build_index.build(knowledge)  # rewrites in place; compare fresh vs saved snapshot
    for bucket, saved in on_disk.items():
        fresh = (knowledge / bucket / "INDEX.md").read_text()
        if fresh != saved:
            errors.append(f"{bucket}/INDEX.md stale — run `just knowledge-index` (drift)")
    if root_disk is not None and (knowledge / "INDEX.md").read_text() != root_disk:
        errors.append("INDEX.md stale — run `just knowledge-index` (drift)")
    return errors


def _check_scenarios(knowledge: Path) -> list[str]:
    errors: list[str] = []
    root = knowledge / "INDEX.md"
    if not root.exists():
        return ["knowledge/INDEX.md missing"]
    text = root.read_text().split(_shared.LEAVES_START)[0]
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
        for name in POINTER_RE.findall(skill_md.read_text()):
            if name.strip() not in known:
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
```

**Note on drift check:** `_check_drift` snapshots disk content, runs `build()` (which rewrites files), then compares the rewritten files against the snapshot. After a clean run files are unchanged. This means running `check` always leaves indexes freshly built — acceptable since the pre-commit hook re-stages nothing and `just knowledge-index` is the canonical regen path.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --with pytest pytest scripts/knowledge/test_knowledge.py -v`
Expected: PASS (all)

- [ ] **Step 5: Run validator against real tree**

Run: `uv run scripts/knowledge/check_index.py`
Expected: prints `knowledge layer OK`, exit 0.

- [ ] **Step 6: Commit**

```bash
git add scripts/knowledge/check_index.py scripts/knowledge/test_knowledge.py knowledge/
git commit -m "feat(knowledge): frontmatter + INDEX + pointer validator"
```

---

## Task 4: Wire into justfile + pre-commit

**Files:**
- Modify: `justfile` (append two recipes)
- Modify: `.pre-commit-config.yaml` (append local hook)

- [ ] **Step 1: Add justfile recipes**

Append to `justfile`:

```
# Regenerate knowledge INDEX files from leaf frontmatter
knowledge-index:
    uv run scripts/knowledge/build_index.py

# Validate knowledge frontmatter, INDEX freshness, scenario + pointer integrity
knowledge-check:
    uv run scripts/knowledge/check_index.py
```

- [ ] **Step 2: Verify recipes run**

Run: `just knowledge-index && just knowledge-check`
Expected: `knowledge indexes rebuilt` then `knowledge layer OK`.

- [ ] **Step 3: Add pre-commit local hook**

Append to `.pre-commit-config.yaml` (as a new top-level entry under `repos:`):

```yaml
  # Knowledge layer validation
  - repo: local
    hooks:
      - id: knowledge-index
        name: "🧭 Knowledge layer validation (frontmatter + INDEX + pointers)"
        entry: uv run scripts/knowledge/check_index.py
        language: system
        pass_filenames: false
        files: ^(knowledge/.*\.md|scripts/knowledge/.*|\.claude/skills/.*\.md)$
```

- [ ] **Step 4: Verify hook runs**

Run: `uv run pre-commit run knowledge-index --all-files`
Expected: hook passes (`knowledge layer OK`).

- [ ] **Step 5: Commit**

```bash
git add justfile .pre-commit-config.yaml
git commit -m "build(knowledge): wire validation into just + pre-commit"
```

---

## Task 5: Seed leaves + scenarios

**Files:**
- Create: `knowledge/ops/reload-after-push.md`, `knowledge/ops/never-push-main.md`, `knowledge/ops/sandbox-homeassistant-local.md`
- Create: `knowledge/integrations/satel-entities.md`, `knowledge/integrations/entity-source-not-in-repo.md`
- Create: `knowledge/areas/occupancy-state-machine.md`
- Create: `knowledge/tooling/dashboard-url-hyphen.md`, `knowledge/tooling/playwright-validate-dashboards.md`, `knowledge/tooling/mushroom-visibility-gotcha.md`
- Modify: `knowledge/INDEX.md` (scenarios section)

- [ ] **Step 1: Write ops leaves**

`knowledge/ops/reload-after-push.md`:

```markdown
---
summary: After every push, reload HA core config and check logs — errors stay hidden until reload.
before_action:
  - About to push a config change that must take effect on HA
  - About to verify a config change live
on_symptom:
  - "config change pushed but behaviour unchanged"
  - "no error in HA but new YAML seems ignored"
---

# Reload after push

HA auto-pulls the current git branch. Local edits are NOT live until pushed.

## Gotchas

- **Reload after every push.** Call `homeassistant.reload_core_config` (MCP/API) then check logs. Config errors stay invisible until a reload happens.
- **Push first when debugging with Playwright.** Edits aren't live pre-push; push, reload, then refresh the page.
```

`knowledge/ops/never-push-main.md`:

```markdown
---
summary: Never push to main — feature branch + PR only.
before_action:
  - About to commit or push a config change
  - About to create a branch for new work
on_symptom:
  - "on main branch with local changes"
---

# Never push to main

## Gotchas

- **Never push to `main`.** Use a feature branch + PR. `no-commit-to-branch` pre-commit hook blocks direct commits to main/master.
```

`knowledge/ops/sandbox-homeassistant-local.md`:

```markdown
---
summary: Sandbox blocks homeassistant.local — curl against HA needs dangerouslyDisableSandbox.
before_action:
  - About to curl or websocat the HA instance
on_symptom:
  - "connection refused or blocked hitting homeassistant.local"
  - "curl to HA times out in sandbox"
---

# Sandbox + homeassistant.local

## Gotchas

- **Sandbox blocks `homeassistant.local`.** curl/websocat against HA needs `dangerouslyDisableSandbox: true` on the Bash call.
- **Env vars are preloaded via direnv.** Use `$HA_URL`, `$HA_TOKEN`, `$API_ACCESS_TOKEN` directly. `.env` reads are hook-blocked — never source the dotenv file.
```

- [ ] **Step 2: Write integrations leaves**

`knowledge/integrations/satel-entities.md`:

```markdown
---
summary: Satel ETHM-1 at 192.168.100.7; entity names lack "satel" — query by config_entry_id.
before_action:
  - About to find or control a Satel alarm entity
  - About to work with the alarm panel, garage door, or a motion/door zone
on_symptom:
  - "grep for satel returns no entities"
  - "cannot locate alarm or zone entity"
---

# Satel Integra alarm

ETHM-1 Plus module at **192.168.100.7** (not .1 — that's the UDM gateway). Integration `satel_integra`, config entry `01KJQNXAFJ9VWP5C29P6YY6QH6`. Ports: 7094 (integration), 7090 (GUARDX), 7091 (DLOADX).

## Gotchas

- **Entity names contain no "satel".** Grepping for "satel" finds nothing. Filter the entity registry by `config_entry_id` instead.
- **9 entities:** `alarm_control_panel.main`, `switch.garage_door`, plus motion/door `binary_sensor.*` zones (living_room, vestibule, garage, terrace_left_door, terrace_main_door, garage_door, balcony_door).
```

`knowledge/integrations/entity-source-not-in-repo.md`:

```markdown
---
summary: Many entities come from integrations, not YAML — query live HA, don't grep the repo.
before_action:
  - About to check whether an entity exists
  - About to confirm an entity id before using it
on_symptom:
  - "entity not found by grepping the repo"
  - "automation references an entity absent from any YAML"
---

# Entities aren't all in the repo

## Gotchas

- **Query live HA for entity existence.** Use MCP / `hass-cli` / API — Zigbee, MQTT, Satel, HACS entities aren't referenced in any YAML here. Grepping the repo gives false negatives.
- **Escalation order:** MCP tools → `/cli` (`hass-cli`) → `/api` (curl/websocat) → Playwright (last resort).
```

- [ ] **Step 3: Write areas leaf**

`knowledge/areas/occupancy-state-machine.md`:

```markdown
---
summary: Area automation patterns (occupancy, manual override + safety timeout) live in a rules file.
before_action:
  - About to add or edit an automation in packages/areas
  - About to wire occupancy or presence lighting for a room
on_symptom:
  - "manual light change gets stomped by an automation"
  - "occupancy lighting flickers or won't latch"
---

# Area automation patterns

## Gotchas

- **Patterns are in `.claude/rules/area-patterns.md`.** It auto-loads when editing files under `packages/areas/**`. Covers the occupancy state machine and manual-override + safety-timeout pattern. Read it before hand-rolling.
- **Filename convention:** `{area}_{action}_{trigger}.yaml` with descriptive `alias` + unique `id`.
- **New devices** go in the matching area `config.yaml`; update light groups/templates. Run `/ha-area-docs` after to regenerate the README.
```

- [ ] **Step 4: Write tooling leaves**

`knowledge/tooling/dashboard-url-hyphen.md`:

```markdown
---
summary: Lovelace dashboard URL keys must contain a hyphen or HA rejects config load.
before_action:
  - About to add a lovelace dashboard under lovelace.dashboards
on_symptom:
  - "Url path needs to contain a hyphen"
  - "HA config load fails after adding a dashboard"
---

# Dashboard URL keys need a hyphen

## Gotchas

- **`lovelace.dashboards.<key>` must contain a hyphen** (e.g. `wall-tablet`, `mobile-phone`). `phone:` alone fails config load with "Url path needs to contain a hyphen".
```

`knowledge/tooling/playwright-validate-dashboards.md`:

```markdown
---
summary: Dashboard edits must end with a Playwright visual check; screenshots go in .playwright-mcp/.
before_action:
  - About to finish a dashboard edit
  - About to claim a dashboard change works
on_symptom:
  - "dashboard layout looks wrong or narrow"
  - "section renders blank"
---

# Playwright-validate dashboards

## Gotchas

- **End every dashboard edit with a Playwright visual check.** Non-visual checks alone aren't enough. Push first (edits aren't live until pushed), reload, then snapshot.
- **Save screenshots into `.playwright-mcp/` only**, never the repo root.
- **Dashboards live in `dashboards/{tablet,phone}.yaml`;** each view is a separate file included from the entrypoint. Tablet `home.yaml` uses `sections` layout.
```

`knowledge/tooling/mushroom-visibility-gotcha.md`:

```markdown
---
summary: Avoid mutually-exclusive visibility pairs on mushroom-template-cards; a crashing card kills its section.
before_action:
  - About to add conditional visibility to a mushroom card
  - About to add a mass-player-card or other crash-prone card
on_symptom:
  - "section renders blank or disappears"
  - "TypeError: Cannot set properties of undefined (setting 'hass')"
---

# Mushroom visibility + crashing cards

## Gotchas

- **Avoid mutually-exclusive visibility pairs on mushroom-template-cards.** Prefer one always-visible card that switches content.
- **A crashing card takes down the entire section's rendering.** `mass-player-card` crashes (`TypeError: Cannot set properties of undefined (setting 'hass')`) when entities don't exist or the "Music Assistant Queue Actions" HACS dep is missing. JS file is `mass-player-card.js`.
```

- [ ] **Step 5: Write scenarios into root INDEX**

Edit `knowledge/INDEX.md` — replace the `## Scenarios` line and the blank line before the start marker with:

```markdown
## Scenarios

### Pushing a config change
About to push and need the change live on HA.
Load: `ops/reload-after-push.md`, `ops/never-push-main.md`.

### Querying or controlling HA over the network
About to curl/websocat HA or find an entity.
Load: `ops/sandbox-homeassistant-local.md`, `integrations/entity-source-not-in-repo.md`.

### Working with the Satel alarm
About to find or control an alarm panel, zone, or garage door.
Load: `integrations/satel-entities.md`, `integrations/entity-source-not-in-repo.md`.

### Editing an area package
About to add or edit a room automation, device, or light group.
Load: `areas/occupancy-state-machine.md`.

### Editing a dashboard
About to add/redesign a Lovelace view or card.
Load: `tooling/dashboard-url-hyphen.md`, `tooling/playwright-validate-dashboards.md`, `tooling/mushroom-visibility-gotcha.md`.

```

(Keep the `<!-- LEAVES:START -->` / `<!-- LEAVES:END -->` markers immediately after — bucket pointers regenerate between them.)

- [ ] **Step 6: Rebuild + validate**

Run: `just knowledge-index && just knowledge-check`
Expected: `knowledge indexes rebuilt` then `knowledge layer OK`. Bucket INDEXes now list the seeded leaves with triggers.

- [ ] **Step 7: Run the test suite**

Run: `uv run --with pytest pytest scripts/knowledge/test_knowledge.py -v`
Expected: PASS (all).

- [ ] **Step 8: Commit**

```bash
git add knowledge/
git commit -m "feat(knowledge): seed leaves from CLAUDE.md + memory facts"
```

---

## Task 6: Author the two skills

**Files:**
- Create: `.claude/skills/knowledge-router/SKILL.md`
- Create: `.claude/skills/knowledge-author/SKILL.md`

- [ ] **Step 1: Write knowledge-router SKILL.md**

Create `.claude/skills/knowledge-router/SKILL.md`:

```markdown
---
name: knowledge-router
description: >
  Use before any operational action — pushing config, reloading HA, editing an area package,
  building a dashboard, working with the Satel alarm, finding an entity, querying HA over the
  network. Routes intent to the relevant knowledge leaves via scenarios + bucket scan, and hands
  off to knowledge-author when no leaf exists for a load-bearing topic.
---

# Knowledge Router

Entry point for recall. Run this before operational work, re-routing **per task, not per session**.

## Algorithm

1. Read `knowledge/INDEX.md`; scan the `## Scenarios` section (above `<!-- LEAVES:START -->`).
2. If a scenario matches the intent, load every leaf it prescribes. Done.
3. No scenario match → pick the bucket: `areas/`, `integrations/`, `ops/`, `tooling/`.
4. Read that bucket's `INDEX.md`; match intent against `**before**:` (proactive) or `**symptom**:` (reactive) triggers.
5. Tie-break conflicting leaves via a leaf's `canonical_path` frontmatter.
6. No leaf for a load-bearing topic → invoke the `knowledge-author` skill to write one.

## Notes

- Leaves are loaded on demand; don't preload the whole layer.
- Reference leaves by name in your own notes, never hardcode `knowledge/<bucket>/<leaf>.md` as a "read this first" pointer in skills/docs. Canonical form: *open `knowledge/INDEX.md` and pick the **<leaf-name>** leaf*.
```

- [ ] **Step 2: Write knowledge-author SKILL.md**

Create `.claude/skills/knowledge-author/SKILL.md`:

```markdown
---
name: knowledge-author
description: >
  Use to capture knowledge into the knowledge/ layer — when the user says "capture this",
  "add a leaf for X", "document this gotcha", when a non-obvious gotcha/correction surfaces, when
  a procedure repeats 3+ times, or when knowledge-router finds no leaf for a load-bearing topic.
  Owns dedup, frontmatter, INDEX rebuild, validation, and commit. Never patch leaves inline.
---

# Knowledge Author

Single write path for the knowledge layer. Everything routes through here — no inline leaf edits.

## Entry points

- **User intent:** "capture this", "add a leaf for X", "document this gotcha".
- **Continuous improvement:** non-obvious gotcha discovered, or a procedure run 3+ times across sessions.
- **Router handoff:** `knowledge-router` found no leaf for a load-bearing topic.

## Procedure

1. **Dedup scan.** Search existing leaves (`knowledge/**/*.md`) for the topic. If one exists, edit it; don't create a duplicate.
2. **Pick the bucket:** `areas/` (room packages, automations), `integrations/` (Zigbee/MQTT/Satel/HACS quirks), `ops/` (deploy, reload, push), `tooling/` (skills, scripts, dashboards, dev setup).
3. **Draft frontmatter, confirm with the user:**
   ```yaml
   ---
   summary: <one-line, ≤120 chars>
   canonical_path: <optional — only if this is supportive context for a sibling>
   before_action:
     - About to <verb> <object>
   on_symptom:
     - "<error or state phrase>"
   ---
   ```
   At least one trigger required. Triggers must NOT embed leaf paths.
4. **Write the body.** Rule first, evidence parenthetical. One gotcha = one bullet. Drop articles, restated context, narrative chronology. Soft-cap ~70 lines. Reference siblings by name, not path.
5. **Rebuild:** `just knowledge-index`.
6. **Validate:** `just knowledge-check`. Fix any errors.
7. **Commit:** `git add knowledge/ && git commit -m "feat(knowledge): <leaf-name> leaf"`.
```

- [ ] **Step 3: Validate skills don't break pointer check**

Run: `just knowledge-check`
Expected: `knowledge layer OK` — the router's `pick the **<leaf-name>** leaf` text is a generic template (literal `<leaf-name>`), not a concrete pointer, so it must not trip the validator.

**If it trips:** the `POINTER_RE` matched `<leaf-name>`. Confirm `<leaf-name>` (with angle brackets) isn't a known leaf stem — it isn't, so this only errors if a real pointer is dangling. The template text uses literal angle brackets, which won't match a real leaf name. No fix needed unless a concrete dangling pointer exists.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/knowledge-router .claude/skills/knowledge-author
git commit -m "feat(knowledge): router + author skills"
```

---

## Task 7: Update CLAUDE.md + final verification

**Files:**
- Modify: `CLAUDE.md` (add Knowledge layer section + continuous-improvement bullet)

- [ ] **Step 1: Add Knowledge layer section to CLAUDE.md**

Add a new `## Knowledge layer` section to `CLAUDE.md` (after the `## Architecture` section):

```markdown
## Knowledge layer

`knowledge/` is a frontmatter-routed how-to layer. Leaves live under four buckets — `areas/`, `integrations/`, `ops/`, `tooling/` — each with YAML frontmatter (`summary`, `before_action[]`, `on_symptom[]`) that drives routing. The `knowledge-router` skill is the entry point: it matches intent against scenarios, then scans bucket INDEXes by `before:`/`symptom:` triggers, loading the matching leaf on demand. Re-route per task, not per session.

`knowledge/INDEX.md` mixes hand-edited scenarios (above `<!-- LEAVES:START -->`) with generated bucket pointers (below). Per-bucket INDEX files are fully generated from leaf frontmatter — never hand-edit between the markers. Rebuild with `just knowledge-index`; validate with `just knowledge-check` (also wired into pre-commit).

Skills reference leaves by name, never by path. Canonical form: *open `knowledge/INDEX.md` and pick the **<leaf-name>** leaf* (kebab-case basename). The validator enforces this shape and flags dangling pointers.

**Continuous improvement:** a non-obvious gotcha or correction → invoke the `knowledge-author` skill (handles dedup, frontmatter, validation, commit). Never patch leaves inline.
```

- [ ] **Step 2: Run full validation + tests**

Run:
```bash
just knowledge-index && just knowledge-check
uv run --with pytest pytest scripts/knowledge/test_knowledge.py -v
uv run pre-commit run knowledge-index --all-files
```
Expected: indexes rebuilt, `knowledge layer OK`, all tests pass, pre-commit hook passes.

- [ ] **Step 3: Drift-detection sanity check**

Hand-corrupt a bucket INDEX, confirm the validator catches it, then restore:
```bash
printf '# ops/\n\n<!-- LEAVES:START -->\nDRIFT\n<!-- LEAVES:END -->\n' > knowledge/ops/INDEX.md
just knowledge-check; echo "exit=$?"
just knowledge-index   # restore
```
Expected: `knowledge-check` reports `ops/INDEX.md stale ... (drift)` and exits nonzero, then `knowledge-index` restores it.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md knowledge/
git commit -m "docs(knowledge): document the knowledge layer in CLAUDE.md"
```

---

## Self-review notes

- **Spec coverage:** buckets (T1), leaf format (T1/T5), root+bucket INDEX (T2), build script (T2), check script (T3), all 6 validation checks (T3), justfile + pre-commit (T4), seed leaves + scenarios (T5), both skills (T6), CLAUDE.md (T7). Out-of-scope agents pointer check still implemented (scans skills only). ✓
- **Type consistency:** `parse_frontmatter`, `iter_leaves`, `BUCKETS`, `LEAVES_START/END`, `splice`, `render_leaf_row`, `build`, `check(knowledge, *, claude_root)` used identically across tasks. ✓
- **No placeholders:** every code/edit step shows full content. ✓
- **Drift-check caveat documented:** `_check_drift` rewrites files as a side effect (Task 3 note). Acceptable — regen is idempotent and `just knowledge-index` is the canonical path.
