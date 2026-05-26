# Authoring an automation animation

## 1. Read the automation into phases

Open the target automation YAML. Map trigger → condition → action to a timeline:

> walk in · sensor pulse · light on · dwell · (timeout) light off

Most presence-lighting automations share that shape. Covers = sun event → cover slides.
Humidifier = humidity drops → fan ramps. Pick 3–5 phases; keep the loop ~8–12s.

**Not every automation has a person.** Process/scheduled automations use a "trigger →
targets activate → auto-off" shape with no walking dot. Example (garden irrigation):
`04:00 clock → lawn zones spray → drip soaks → valves auto-close → idle`. Here the
"actors" are valves/zones, not a person — animate their activation (spray rings, fill)
instead of a motion path. The status word still names the current phase.

## 2. Build the static scene from layout.yaml

Read the area's `docs/layout.yaml` (see `layout.schema.md`). If the layout doesn't exist
yet, build it first — prefer reading dimensions off an architect floor plan
(`{area}/docs/floorplan.png`) over asking the user to measure. Then draw, in order:
frame + title → room rectangles → furniture → light elements (off state) → sensors +
labels → door. Scale meters→viewBox (~100 units/m + a ~60-unit top band for the title).
Keep room proportions and relative positions faithful to the plan. Paste the `<defs>`
block from `defs.svg`.

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
  — note: this only disables CSS `animation`; it does **not** stop SMIL `<animate>`/`<animateMotion>`.
  It is a best-effort guard, not a true reduced-motion stop. There is no pure-SMIL way to honour
  the media query inside an `<img>`-embedded SVG, so keep loops calm and non-flashing regardless.

## 5. Verify (MANDATORY — do not skip)

Playwright cannot open `file:` URLs, so serve over http. **Inline the SVG** into the
preview page (not `<img src=>`) — this lets you drive the SMIL clock to an exact phase,
which `<img>`-embedded SVG does NOT allow.

```bash
cd packages/areas/{floor}/{area}/docs
{ printf '<!doctype html><meta charset=utf-8><body style="margin:0;background:#222">'; cat NAME.svg; printf '</body>'; } > _inline.html
python3 -m http.server 8741   # run in background; note its cwd = this dir
```

Then with Playwright MCP, **for each phase** (idle / triggered / active / off):
1. `browser_navigate` → `http://localhost:8741/_inline.html` (path is relative to the
   server's cwd = the docs dir).
2. **Pin the clock to the phase you want** — far more reliable than `browser_wait_for`
   offsets, which drift because SMIL starts late (img decode / full-page-screenshot relayout):
   ```js
   browser_evaluate: () => { const s=document.querySelector('svg'); s.pauseAnimations(); s.setCurrentTime(3.5); return s.getCurrentTime(); }
   ```
   Pick a `setCurrentTime` value inside each phase's keyTimes window × loop `dur`
   (e.g. spray phase 0.16–0.53 of a 10 s loop → set 3.5).
3. `browser_take_screenshot` with `fullPage:true` and an **ABSOLUTE filename** (relative
   paths land in an unpredictable dir; non-fullPage crops a tall SVG).
4. `Read` each screenshot. Confirm: all elements present, the light/valve actually changes,
   the sensor/spray pulses, any motion path is right, the status word matches the phase and
   does not overlap a sibling, nothing clips the viewBox.
5. If wrong, fix the SVG, **rebuild `_inline.html`** (re-run the `cat` line), re-verify.
   Only when correct:

```bash
rm -f _inline.html *.png        # remove temp preview + screenshots
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
