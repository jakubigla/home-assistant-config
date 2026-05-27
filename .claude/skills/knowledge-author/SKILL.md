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

0. **Rent test (gate — reject before writing).** A leaf must beat scanning the repo. Capture ONLY if it passes all three:
   - **Non-discoverable by scan** — grep/reading the obvious file won't surface it (behavioral/timing/API quirk, a 3rd/4th place no grep reaches, a correction to a wrong assumption).
   - **Costs real time or a mistake** if unknown next time.
   - **Not rederivable in <3 tool calls** by reading the named file.

   If the knowledge is **a code change you just made**, the code is the record — do NOT also write a leaf. If it's rederivable by scanning, skip. When a candidate fails, say so and capture nothing. The layer's cost is paid on every route (router reads the whole table) — a leaf that doesn't beat scanning is a net loss.

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
5. **Rebuild:** `just knowledge-index` regenerates the single `knowledge/INDEX.md` table from frontmatter. (Pre-commit also rebuilds + re-stages it, so the committed table can't drift — but run it now to review the row.)
6. **Validate:** `just knowledge-check` (frontmatter schema, table drift, skill pointers). Fix any errors.
7. **Commit:** `git add knowledge/ && git commit -m "feat(knowledge): <leaf-name> leaf"`.
