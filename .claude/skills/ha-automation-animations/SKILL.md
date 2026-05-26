---
name: ha-automation-animations
description: Create animated SVG floor-plan diagrams of Home Assistant automations for area READMEs. Use when the user asks to "animate an automation", "add an animation to the README", "show how an automation works visually", "visualize presence/lighting/covers", or to diagram a room's automation behavior. One automation = one animated SVG, embedded in the area's README.
---

# HA automation animations

Hand-author a verified animated **SVG floor-plan** showing how one HA automation behaves
(top-down room: person walks in, sensors pulse, lights glow, timeout off). One automation
= one SVG, stored in `{area}/docs/` and embedded in the area README.

This skill is a **method**, not a generator. Read the automation, design the animation,
hand-write the SVG modeled on the reference, then verify it renders correctly.

## Reference files (read these first)

- `reference/presence-lighting.svg` — the gold render. Mirror its structure, palette, timing.
- `reference/defs.svg` — copy-paste `<defs>` (glow/foot/lampcast) + palette + easing notes.
- `reference/layout.schema.md` — the per-area `layout.yaml` geometry schema + bedroom example.
- `reference/AUTHORING.md` — full method, layer conventions, learned bugs, the verify loop.

## Checklist (create a TodoWrite item per step)

1. **Identify** the target area + automation. Read the automation YAML.
2. **Geometry:** open `{area}/docs/layout.yaml`. If missing, create it per `layout.schema.md`
   — ask the user for room size + furniture/sensor/door positions; never guess geometry.
3. **Author** the SVG per `AUTHORING.md`: phases → static scene → animation layer →
   a11y/reduced-motion. Paste `defs.svg`. Model on `presence-lighting.svg`.
4. **Verify (mandatory):** serve over http + Playwright screenshot each phase + Read +
   confirm (full loop in `AUTHORING.md` §5). Fix and re-verify until correct.
5. **Embed** in the README under the matching "How It Works" subsection, wrapped in
   `<!-- svg:keep -->` markers (`AUTHORING.md` §6).
6. **Clean up** temp preview files + server, then commit the SVG + README + any new layout.yaml.

## Notes
- SMIL only (GitHub renders SVG via `<img>` — no CSS/JS). `viewBox`, no width/height.
- Push to deploy is NOT needed for README SVGs (they render from the repo on GitHub),
  but follow the repo's normal branch/PR rules for the commit.
