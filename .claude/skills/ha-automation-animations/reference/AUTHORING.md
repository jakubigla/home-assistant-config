# Authoring an automation animation

## 1. Read the automation into phases

Open the target automation YAML. Map trigger → condition → action to a timeline:

> walk in · sensor pulse · light on · dwell · (timeout) light off

Most presence-lighting automations share that shape. Covers = sun event → cover slides.
Humidifier = humidity drops → fan ramps. Pick 3–5 phases; keep the loop ~8–12s.

## 2. Build the static scene from layout.yaml

Read the area's `docs/layout.yaml` (see `layout.schema.md`). Draw, in order:
frame + title → room rectangles → furniture → light elements (off state) → sensors +
labels → door. Scale meters→viewBox (~100 units/m + a ~60-unit top band for the title).
Paste the `<defs>` block from `defs.svg`.

## 3. Add the animation layer

| Layer | How |
|-------|-----|
| Person | Blue dot (`#7fd1ff`) + radial `url(#foot)` glow, grouped. `animateMotion` along the walk path with `keySplines` ease-out arrival. Group `opacity` 0 while "outside" before/after. |
| Sensor trigger | Cone/zone polygon, `fill` PIR-green. Breathing `opacity` pulse (e.g. `0;0;0.40;0.12;0.40;0`) timed to entry — never a hard on/off flash. |
| Light on | Target element `fill` → `#ffd17a` with `calcMode="spline"`; add a `url(#lampcast)` ellipse over the room for spill; wrap the light in `filter="url(#glow)"`. |
| Status word | N stacked `<text>` rows at the SAME x/y, ONE visible per phase via opacity keyTimes. |

Share **one keyTimes vocabulary** across every `<animate>` so layers line up.

## Learned bugs (do not repeat)

- **tspan overlap:** status words as `<tspan>` sharing one text anchor render on top of
  each other. Use separate stacked `<text>` elements, one visible per phase.
- **Label inside a box:** status/labels placed at coordinates that fall inside a room box
  collide visually. Keep status in the top band (y≈40).
- **animateMotion snap:** without `keyPoints`+`keySplines`, the dot teleports between
  segments. Provide both, with a held segment (`0 0 1 1`) for the dwell.

## 4. Accessibility + resilience (always include)

- `viewBox` only, no hardcoded width/height.
- `role="img"`, a `<title>` and `<desc>`.
- `<style>@media (prefers-reduced-motion: reduce){ svg * { animation:none !important; } }</style>`

## 5. Verify (MANDATORY — do not skip)

Playwright cannot open `file:` URLs, so serve over http.

```bash
cd packages/areas/{floor}/{area}/docs
printf '<!doctype html><meta charset=utf-8><body style="background:#222"><img src="NAME.svg"></body>' > _preview.html
python3 -m http.server 8741   # run in background; note its cwd = this dir
```

Then with Playwright MCP:
1. `browser_navigate` → `http://localhost:8741/_preview.html` (path is relative to the
   server's cwd, which is the docs dir).
2. `browser_navigate` again to **reset the animation clock to t=0**.
3. For each phase: `browser_wait_for` the phase offset, then `browser_take_screenshot`
   with an **ABSOLUTE filename** (relative paths land in an unpredictable dir).
4. `Read` each screenshot. Confirm: all elements present, the light actually changes
   color, the sensor pulses, the person walks the path, the status word matches the
   phase, nothing overlaps or clips.
5. If wrong, fix the SVG and re-verify. Only when correct:

```bash
rm -f _preview.html *.png        # remove temp preview + screenshots
# kill the background http.server
```

## 6. Embed in the README

Under the matching "How It Works" subsection, add:

```html
<!-- svg:keep -->
<img src="docs/NAME.svg" alt="Animated diagram: <one-line behavior>">
<!-- /svg:keep -->
```

The `svg:keep` markers flag the block so a future `/ha-area-docs` regen preserves it.
(Auto-preservation in ha-area-docs is a separate follow-up; the markers are the contract.)
