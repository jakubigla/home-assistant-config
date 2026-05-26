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
4. **Read that bucket's `INDEX.md` and scan every `**before**:` / `**symptom**:` trigger. Picking a bucket is NOT an exit — you have not routed until you have either loaded a matching leaf or read the whole bucket index and confirmed none matches.** Match on the *task domain* (e.g. "irrigation schedule"), not on whichever files you happen to have open.
5. Tie-break conflicting leaves via a leaf's `canonical_path` frontmatter.
6. No leaf for a load-bearing topic → invoke the `knowledge-author` skill to write one.

## Stop signs — you skipped the scan if:

- You stopped after "this is an `areas/` task" without opening `areas/INDEX.md`.
- You ran `grep`/`find` to locate config files and started editing. **Grep finds files; it does not find gotchas.** A leaf can name a 3rd/4th place (a dashboard macro, a sibling sensor) that no grep of the obvious package will surface. Finish the bucket scan *before* editing.
- A leaf you loaded names files — you must touch **every** file it lists, not just the one you came for.

## Notes

- Leaves are loaded on demand; don't preload the whole layer.
- Reference leaves by name, never hardcode `knowledge/<bucket>/<leaf>.md` as a "read this first" pointer in skills or docs. Canonical form: open `knowledge/INDEX.md` and pick the **reload-after-push** leaf (use the kebab-case basename of whichever leaf you mean).
