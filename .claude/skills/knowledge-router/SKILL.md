---
name: knowledge-router
description: >
  Use before any operational action — pushing config, reloading HA, editing an area package,
  building a dashboard, working with the Satel alarm, finding an entity, querying HA over the
  network. Routes intent to the relevant knowledge leaves via the single INDEX table, and hands
  off to knowledge-author when no leaf exists for a load-bearing topic.
---

# Knowledge Router

Entry point for recall. Run this before operational work, re-routing **per task, not per session**.

## Algorithm

1. Read `knowledge/INDEX.md` — one flat table, every leaf, columns `Leaf | Summary | Triggers`.
2. Scan the **Triggers** column for a row matching the intent (match on the *task domain* — "irrigation schedule" — not on whichever files you happen to have open). `before:` = "about to X" actions; `symptom:` = error/state phrases. The `Summary` confirms a near-match is the right row.
3. Match → load that leaf (the `Leaf` cell links to its path). Done.
4. **No exit until you have either loaded a matching leaf or read the whole table and confirmed none matches.** Reading one table is the entire scan — there is no second hop.
5. No leaf for a load-bearing topic → invoke the `knowledge-author` skill to write one.

## Stop signs — you skipped the scan if:

- You started editing without reading the INDEX table.
- You ran `grep`/`find` to locate config files and started editing. **Grep finds files; it does not find gotchas.** A leaf can name a 3rd/4th place (a dashboard macro, a sibling sensor) that no grep of the obvious package will surface. Finish the table scan *before* editing.
- A leaf you loaded names files — you must touch **every** file it lists, not just the one you came for.

## Notes

- Leaves are loaded on demand; load only the rows you match, not the whole layer.
- Reference leaves by name, never hardcode `knowledge/<bucket>/<leaf>.md` as a "read this first" pointer in skills or docs. Canonical form: open `knowledge/INDEX.md` and pick the **reload-after-push** leaf (use the kebab-case basename of whichever leaf you mean).
