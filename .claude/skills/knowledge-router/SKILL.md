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
- Reference leaves by name, never hardcode `knowledge/<bucket>/<leaf>.md` as a "read this first" pointer in skills or docs. Canonical form: open `knowledge/INDEX.md` and pick the **reload-after-push** leaf (use the kebab-case basename of whichever leaf you mean).
