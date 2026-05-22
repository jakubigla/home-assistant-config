---
summary: Area automation patterns (occupancy, manual override + safety timeout) live in a rules file.
before_action:
  - About to add or edit an automation in an area package
  - About to wire occupancy or presence lighting for a room
on_symptom:
  - "manual light change gets stomped by an automation"
  - "occupancy lighting flickers or won't latch"
---

# Area automation patterns

## Gotchas

- **Patterns are in `.claude/rules/area-patterns.md`.** It auto-loads when editing files under `packages/areas/`. Covers the occupancy state machine and manual-override + safety-timeout pattern. Read it before hand-rolling.
- **Filename convention:** `{area}_{action}_{trigger}.yaml` with descriptive `alias` + unique `id`.
- **New devices** go in the matching area `config.yaml`; update light groups/templates. Run `/ha-area-docs` after to regenerate the README.
