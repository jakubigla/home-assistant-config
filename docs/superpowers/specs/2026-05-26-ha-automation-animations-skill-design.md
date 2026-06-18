# ha-automation-animations skill — design

**Date:** 2026-05-26
**Status:** approved-pending-review
**Origin:** Built a verified animated SVG for the bedroom presence-lighting automation (top-down floor plan: person walks door→bed, PIR cone pulses, bed stripe glows on, vacant→off). Want to repeat this for other areas/automations via a reusable skill.

## Goal

A project skill that guides Claude to hand-author **animated SVG floor-plan diagrams** of Home Assistant automations, one SVG per automation, embedded into area READMEs. The skill is a *method* (instructions + reference + schema + verified loop), not a code generator.

## Decisions (locked during brainstorm)

| Topic | Decision |
|-------|----------|
| Visual style | Top-down floor plan. Room boxes, furniture, sensor positions, walking person dot, glowing lights, sensor cones. |
| Animation unit | **One automation = one SVG.** An area README embeds several. |
| Skill model | **Guided hand-authoring.** Skill = SKILL.md instructions + the verified bedroom reference SVG + reusable `<defs>` (glow, foot-glow, lamp-cast, easing keySplines) + the layout.yaml schema + verify loop. Claude reads the automation YAML, designs the animation, hand-writes the SVG each time. No rigid script. |
| Geometry input | **Per-area `layout.yaml`** — user/Claude fills room dimensions, furniture boxes, sensor positions, door, walk path. Only hand-fed input; cannot be inferred from automation YAML. |
| Tech | SMIL animation (`<animate>`, `<animateMotion>`, `<animateTransform>`). Required because GitHub renders SVG via `<img>` where CSS/JS don't run. `viewBox`, no hardcoded width/height. `prefers-reduced-motion` guard. `<title>`/`<desc>` for a11y. |
| Verification | **Mandatory.** Serve SVG over local http, Playwright screenshot at each animation phase, confirm render + timing, only then done. (file: protocol is blocked in Playwright — must serve over http.) |
| Storage + embed | SVGs in `{area}/docs/*.svg`. Embedded inline via `<img src="docs/{name}.svg">` next to the matching section in the existing README "How It Works" heading. |
| Skill name/scope | `ha-automation-animations`, **project skill** in `.claude/skills/`. HA-aware. |

## Architecture

```
.claude/skills/ha-automation-animations/
  SKILL.md                  # method + checklist + frontmatter triggers
  reference/
    presence-lighting.svg   # the verified bedroom SVG = gold reference
    layout.schema.md        # layout.yaml field reference + example
    defs.svg                # copy-paste reusable <defs>: glow, foot, lampcast, easing splines

packages/areas/{floor}/{area}/
  docs/
    layout.yaml             # per-area geometry (authored once, reused by all its SVGs)
    {automation}.svg        # e.g. presence-lighting.svg, covers.svg, humidifier.svg
  README.md                 # <img> embeds inline under matching How-It-Works section
```

### layout.yaml schema (per area, reused across that area's SVGs)

Real-world units (meters); the skill scales to a `viewBox`. One file per area, since geometry is shared across that room's automations.

```yaml
# packages/areas/first-floor/bedroom/docs/layout.yaml
area: bedroom
rooms:                         # one or more boxes (main + ensuite + wardrobe)
  - id: bedroom   {x: 0,   y: 0,   w: 4.1, h: 4.0}
  - id: ensuite   {x: 4.2, y: 0,   w: 1.4, h: 2.2, label: "ensuite"}
  - id: wardrobe  {x: 4.2, y: 2.4, w: 1.4, h: 1.4}
furniture:
  - {id: bed, room: bedroom, x: 0.3, y: 0.3, w: 1.5, h: 0.9, label: bed}
sensors:
  - {id: pir,    type: pir,    room: bedroom, x: 2.0, y: 3.9, label: "PIR (entrance)"}
  - {id: mmwave, type: mmwave, room: ensuite, x: 0.7, y: 0.8}
lights:
  - {id: stripe, room: bedroom, x: 0.3, y: 1.9, w: 1.5, kind: strip, label: "bed stripe"}
door: {room: bedroom, x: 1.6, w: 0.7, side: bottom}
paths:                         # named walk paths, referenced by an animation
  enter_to_bed: [door, {x: 1.5, y: 1.9}]   # door -> bedside
```

### Per-SVG authoring (what Claude does each time)

The skill does NOT store per-automation recipes. Claude:
1. Reads the target automation YAML (trigger → condition → action).
2. Picks the layout elements involved (which sensor triggers, which light is the action, which path the person walks).
3. Designs a loop with phases (e.g. `walk in · sensor pulse · light on · dwell · vacancy → off`), copies `defs.svg`, hand-writes the SVG modeled on the reference.
4. Verifies (below).

## Animation conventions (from the verified bedroom SVG)

- **Single loop**, ~8–12s, `repeatCount="indefinite"`.
- **Phases** expressed via shared `keyTimes` across animates so layers stay in sync.
- **Person** = blue dot + radial foot-glow group, moves on `animateMotion` with `keySplines` ease-in/out; group opacity hides it "outside" before/after.
- **Sensor trigger** = colored cone/zone, breathing opacity pulse (not hard flash) timed to entry.
- **Light on** = element `fill` → warm color with spline easing + a radial `lampcast` ellipse for room glow + `feGaussianBlur` glow filter.
- **Status word** = one of N stacked `<text>` rows, one visible per phase (NOT tspans sharing an anchor — that overlaps; learned bug).
- **Colors:** bg `#0f1420`, walls `#161d2c`/stroke `#2b3850`, person `#7fd1ff`, warm light `#ffd17a`, PIR cone green `#2e7d32`, muted labels `#46566e`.

## Verification loop (mandatory, in checklist)

1. Wrap SVG in a tiny `_preview.html` (`<img src=...>`), serve dir: `python3 -m http.server PORT`.
2. Playwright `browser_navigate` to `http://localhost:PORT/_preview.html` (file: is blocked).
3. Reload to reset t=0, `browser_wait_for` to each phase offset, `browser_take_screenshot` with an **absolute filename** (relative saves land in an unpredictable dir).
4. Read screenshots, confirm: elements present, light actually changes color, sensor pulses, person walks the path, status word matches phase, no overlap/clipping.
5. Clean up temp files (`_preview.html`, screenshots) and kill the server.

## README integration

- Embed inline: under the relevant How-It-Works subsection, place `<img src="docs/{automation}.svg" alt="...">` immediately before/after the prose that describes it.
- **/ha-area-docs collision risk:** that skill regenerates READMEs and may overwrite embeds. Mitigation documented in SKILL.md: wrap each embed in `<!-- svg:keep -->`…`<!-- /svg:keep -->` markers and note that ha-area-docs should preserve marked blocks. (Wiring ha-area-docs to auto-preserve is out of scope for v1 — flagged as a follow-up.)

## Non-goals (YAGNI)

- No code generator / no per-automation recipe DSL.
- No auto-inference of geometry from YAML (impossible — hand-fed layout).
- No multi-automation cycling in one SVG (one automation = one SVG).
- No editing of the `ha-area-docs` skill in v1 (just the marker convention).
- No GIF/video output (SVG only; smaller, sharper, version-controllable).

## Success criteria

- Running the skill on a named area+automation produces a verified animated SVG in `{area}/docs/`, embedded in the README, rendering correctly on GitHub.
- A second automation in the same area reuses the existing `layout.yaml` without re-authoring geometry.
- The bedroom `presence-lighting.svg` (already built + verified) is adopted as the reference and its README is the first embed.

## Open follow-ups (post-v1)

- Wire `/ha-area-docs` to preserve `svg:keep` blocks automatically.
- Backfill `layout.yaml` + SVGs for remaining areas (batched, user-reviewed).
- Capture a knowledge leaf for the "file: blocked → serve over http; absolute screenshot path" Playwright gotcha if not already covered.
