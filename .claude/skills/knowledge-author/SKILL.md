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
