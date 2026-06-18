# Knowledge Layer — Design

Port the frontmatter-routed knowledge layer from `feedbacks-app` into `home-assistant-config`, adapted to this repo's conventions (`just` recipes instead of `mise`, PEP 723 `uv` scripts instead of bash-wrapper + `_py`).

## Goal

A how-to layer of small markdown "leaves" that are discovered by intent (frontmatter triggers), kept fresh by generated indexes, and validated on commit. Two skills bracket it: a **router** (recall) and an **author** (write). Replaces ad-hoc knowledge scattered across `CLAUDE.md` and auto-memory with a single, routable, validated layer.

## Directory layout

```
knowledge/
├── INDEX.md                    # scenarios (hand-edited) + bucket pointers (generated)
├── areas/
│   ├── INDEX.md                # generated
│   └── *.md                    # leaves: room packages, automations, occupancy
├── integrations/
│   ├── INDEX.md                # generated
│   └── *.md                    # leaves: Zigbee/MQTT/Satel/HACS quirks
├── ops/
│   ├── INDEX.md                # generated
│   └── *.md                    # leaves: deploy, reload, push/branch discipline
└── tooling/
    ├── INDEX.md                # generated
    └── *.md                    # leaves: skills, scripts, dev setup

scripts/knowledge/
├── build_index.py              # PEP 723 uv script — regenerate INDEXes
└── check_index.py              # PEP 723 uv script — validate

.claude/skills/
├── knowledge-router/SKILL.md
└── knowledge-author/SKILL.md
```

### Buckets

- `areas/` — per-room packages, automations, occupancy state machine, light groups. Maps to `packages/areas/{floor}/{area}/`.
- `integrations/` — quirks of Zigbee/MQTT/Satel/HACS and other integrations whose entities aren't in YAML.
- `ops/` — deployment: HA auto-pull, reload-after-push, never-push-main, sandbox network limits.
- `tooling/` — Claude skills, scripts, dashboards tooling, dev environment.

## Leaf format

YAML frontmatter + markdown body.

```yaml
---
summary: <one-line, ≤120 chars, what the leaf covers>
canonical_path: <optional — only when this leaf is supportive context for a sibling>
before_action:
  - About to <verb> <object>
on_symptom:
  - "<error or state phrase>"
---

# Title

Prose intro (one or two sentences of orientation).

## Gotchas

- **Bold rule first.** Evidence parenthetical. One gotcha = one bullet.
```

Body discipline:
- Rule first, evidence parenthetical.
- One gotcha = one bullet.
- Drop articles, restated context, narrative chronology.
- Reference sibling leaves by **name**, never by path.
- Soft-cap ~70 lines (validator warns, never blocks).

At least one trigger required (`before_action` or `on_symptom`). Triggers must NOT embed leaf paths (decoupling).

## Index files

### Root `knowledge/INDEX.md`

Two regions:
1. **Scenarios** (hand-edited, above `<!-- LEAVES:START -->`): named operational situations with prescribed leaf loads.
   ```markdown
   ## Scenarios

   ### Pushing a config change
   About to push and need the change live on HA.
   Load: `ops/reload-after-push.md`, `ops/never-push-main.md`.
   ```
2. **Bucket pointers** (generated, between markers): `### areas/` → `See \`areas/INDEX.md\`.`

### Bucket `knowledge/{bucket}/INDEX.md`

Fully generated between `<!-- LEAVES:START -->` / `<!-- LEAVES:END -->`. Each leaf:
```markdown
- [leaf-name](leaf-name.md) — summary line.
  - **before**: trigger; trigger
  - **symptom**: trigger; trigger
```

## Scripts

Both PEP 723 `uv run --script` files (match `flight-tracker/scripts/download_data.py`). Shebang `#!/usr/bin/env -S uv run --script`, inline `# /// script` metadata, `requires-python = ">=3.11"`. PyYAML for frontmatter parsing.

### `build_index.py`

`build(knowledge_root)`:
1. Collect `knowledge/{areas,integrations,ops,tooling}/*.md` excluding `INDEX.md`.
2. Parse YAML frontmatter per leaf.
3. Group by bucket; render leaf rows + trigger lines.
4. Splice into each bucket `INDEX.md` between markers.
5. Render root `INDEX.md` bucket pointers between markers; preserve scenarios above start marker.

Idempotent: running twice produces no diff.

### `check_index.py`

`check(knowledge_root, claude_root)` returns aggregated errors. Checks:
1. **Frontmatter schema** — `summary` present + ≤120 chars; ≥1 trigger.
2. **Trigger decoupling** — no `bucket/leaf.md` substring inside any trigger.
3. **INDEX drift** — disk INDEX == fresh generator output (run build in-memory, compare).
4. **Scenario references** — every leaf path named in scenarios exists.
5. **Skill pointer integrity** — every `pick(?:ing)? (?:the )?\*\*([^*]+)\*\* leaf` match in `.claude/skills/**/*.md` resolves to a real leaf name surfaced in some bucket INDEX.
6. **Body length** — soft warning above ~70 lines; advisory, never fatal.

Exit nonzero on any fatal error; print warnings without failing.

## Skills

### `knowledge-router/SKILL.md`

Entry point before any operational action. Algorithm:
1. Read root `INDEX.md`, scan `## Scenarios`.
2. Match intent against scenario descriptions → load prescribed leaves.
3. No scenario → pick bucket (areas/integrations/ops/tooling).
4. Read bucket INDEX, match intent against `before:` (proactive) / `symptom:` (reactive).
5. Tie-break via `canonical_path`.
6. No leaf for a load-bearing topic → invoke `knowledge-author`.

Re-route per task, not per session.

### `knowledge-author/SKILL.md`

Write side. Entry points: explicit user intent ("capture this"), continuous-improvement signal (gotcha / 3+ repeat), router gap handoff. Owns:
1. Dedup scan (search existing leaves first).
2. Bucket selection + draft frontmatter (confirm with user).
3. Write leaf body (discipline rules above).
4. `just knowledge-index` to rebuild.
5. `just knowledge-check` to validate.
6. Commit.

Never patch leaves inline outside this skill.

## Integration

### justfile

```
# Regenerate knowledge INDEX files from leaf frontmatter
knowledge-index:
    uv run scripts/knowledge/build_index.py

# Validate knowledge frontmatter, INDEX freshness, scenario + pointer integrity
knowledge-check:
    uv run scripts/knowledge/check_index.py
```

### .pre-commit-config.yaml

Local hook:
```yaml
  - repo: local
    hooks:
      - id: knowledge-index
        name: "🧭 Knowledge layer validation (frontmatter + INDEX + pointers)"
        entry: uv run scripts/knowledge/check_index.py
        language: system
        pass_filenames: false
        files: ^(knowledge/.*\.md|scripts/knowledge/.*|\.claude/skills/.*\.md)$
```

### CLAUDE.md

Add a `## Knowledge layer` section describing the routed layer, the router/author skills, the generated-vs-hand-edited INDEX split, `just knowledge-index` / `knowledge-check`, and the name-not-path pointer convention. Add a continuous-improvement bullet: non-obvious gotcha → invoke `knowledge-author`, never patch inline.

## Seed leaves

Authored from existing `CLAUDE.md` + auto-memory facts.

| Bucket | Leaf | Source |
|---|---|---|
| ops | `reload-after-push` | reload core config + check logs after every push |
| ops | `never-push-main` | feature branch + PR only |
| ops | `sandbox-homeassistant-local` | sandbox blocks `homeassistant.local`; needs `dangerouslyDisableSandbox` |
| integrations | `satel-entities` | ETHM-1 at .7; entity names lack "satel"; query by config_entry_id |
| integrations | `entity-source-not-in-repo` | query live HA for entities, don't grep repo |
| areas | `occupancy-state-machine` | refs `.claude/rules/area-patterns.md` |
| tooling | `dashboard-url-hyphen` | lovelace dashboard keys must contain a hyphen |
| tooling | `playwright-validate-dashboards` | dashboard edits end with Playwright visual check; screenshots in `.playwright-mcp/` |
| tooling | `mushroom-visibility-gotcha` | avoid mutually-exclusive visibility pairs on mushroom-template-cards |

Root `INDEX.md` scenarios seeded: "Pushing a config change", "Editing a dashboard", "Working with Satel alarm", "Adding/editing an area package".

## Out of scope

- Migrating `CLAUDE.md` / auto-memory content out wholesale — seed leaves only; full migration is incremental via `knowledge-author`.
- Agents referencing knowledge (source repo has it; this repo has no `.claude/agents/`). Pointer check still scans skills.

## Testing / verification

- `just knowledge-index` produces no diff on second run (idempotent).
- `just knowledge-check` passes clean on seeded content.
- Introduce a deliberate drift (edit a bucket INDEX by hand) → `knowledge-check` flags it.
- Introduce a bad pointer in a skill → check flags it.
- `uv run pre-commit run knowledge-index --all-files` passes.
