# Outdoor View Redesign — Design Spec

**Date:** 2026-06-18
**Branch:** `chore/june-features`
**File touched:** `dashboards/tablet/outdoor.yaml` (full rewrite)
**New helper:** `input_boolean.garden_show_tuning` — *only if expander-card is unavailable* (see Open Dependency).
**New HACS dependency:** `lovelace-expander-card` (user installs).
**Status:** Design approved by user; awaiting written-spec review.

## Goal

The Outdoor view (`/wall-tablet/outdoor`) packs all the right functionality but
wastes space and reads in the wrong order. The current layout is a single
`type: sections` view with one `column_span: 3` section wrapping rigid
`horizontal-stack` two-column bands. Because the left column (Garden controls:
mode select, two chip rows, soil row, verdict, threshold sliders, one-off
scheduler, run-lawn) is far taller than the right column (7-day table + three
Run-Now buttons), the right column ends early and leaves a large dead band of
whitespace. Status data the user mainly wants to *glance at* (drip/lawn times,
soil, doors, gates) is scattered across separate cards rather than surfaced as
a single scannable row.

Primary use case: **glance status**. The user mostly reads the view (is drip/lawn
OK, soil levels, doors/gates closed) and only occasionally taps to run irrigation
or tune thresholds.

The redesign:

- Adds an **At-a-Glance** full-width chip band at the top (under weather) that
  consolidates drip/lawn/next-run + all door/gate/porch status into one row.
- Drops the rigid `column_span: 3` single-section wrapper in favour of **real
  `type: sections` masonry auto-flow** (`max_columns: 3`) so HA packs short and
  tall cards together and eliminates the dead band.
- Tucks the four Smart-drip **threshold sliders into a collapsible expander**
  (`custom:expander-card`), collapsed by default, since they are set rarely and
  read never.
- Groups everything into three logical clusters in glance-first order:
  **Status → Irrigation → Structure**.

## Non-goals

- No change to irrigation *logic* — the brain, skip sensors, soil-driven drip
  automations, and the `input_number` thresholds shipped earlier this session
  all stay exactly as they are. This is a pure presentation rewrite.
- No new scripts, sensors, or automations (the one possible exception is
  `input_boolean.garden_show_tuning`, and only as a fallback — see Open
  Dependency).
- No change to the other tablet views or the phone dashboard.
- Not adding new device controls beyond what the view already exposes.

## Layout

```
┌─────────────────────────────────────────────────────────────┐
│  WEATHER HERO  (full width, weather-forecast, hourly strip)  │
└─────────────────────────────────────────────────────────────┘

┌─── AT A GLANCE  (full-width chips band) ────────────────────┐
│  💧 Drip: Thu 16:28   🌱 Lawn: Wed 17:14   ⏱ Next: Sat 04:00 │
│  🚪 Terrace: Closed   🚪 Left: Closed   🌙 Porch             │
│  🚧 Park gate: Closed   🏠 Garage: Closed                    │
└─────────────────────────────────────────────────────────────┘

   ── masonry auto-flow below: HA packs these by height ──

┌─ SOIL & DRIP  (Smart-only) ─┐  ┌─ 7-DAY SCHEDULE ───────────┐
│ 💧 L 85%  R 85%  Sona 93%   │  │ Day  Lawn  Zones    Drip   │
│ Wet (85%) · waits >60%      │  │ Thu  ✓30m  30·18·18 💧soil │
│ ▸ Tuning  (expander)        │  │ …                          │
│    Fire below      35%      │  │ footnote (mode-aware)      │
│    Re-arm above    60%      │  └────────────────────────────┘
│    Saturation veto 70%      │
│    Min days between 1 d     │
└─────────────────────────────┘

┌─ IRRIGATION CONTROL ────────┐  ┌─ RUN NOW ──────────────────┐
│ Mode:       [Smart ▾]       │  │   [Lawn]  [Drip]  [Full]   │
│ One-off:    [Lawn ▾]        │  │   Minutes per zone  10 ──── │
│ When:       [date/time]     │  │   [Run Lawn  zones·min]    │
│ [Schedule]  [Cancel]        │  └────────────────────────────┘
└─────────────────────────────┘

┌─ PERGOLA ───┐ ┌─ GATES ─────┐ ┌─ TERRACE ───┐
│ Roof cover  │ │ Park gate   │ │ door / porch│
│ Weather mode│ │ Garage gate │ │ chips       │
└─────────────┘ └─────────────┘ └─────────────┘
```

## Sections (each a real `type: sections` section)

The view becomes `type: sections`, `max_columns: 3`. Sections that must span
the full width set `column_span: 3`; the rest are left at default span so the
grid masonry-packs them into columns.

1. **Weather** — `column_span: 3`. Unchanged `weather-forecast` hero.

2. **At a Glance** — `column_span: 3`. New `custom:mushroom-chips-card`
   consolidating, in one band:
   - Drip last-run, Lawn last-run, Next-run (moved from the irrigation chip
     rows).
   - Terrace main door, Terrace left door, Porch dark/light (moved from the
     Terrace cluster, which is then removed — see section 9).
   - Park gate state, Garage gate state (read-only status chips; full controls
     remain in the Gates cluster).
   Each chip `tap_action: more-info` on its entity.

3. **Soil & Drip** (default span) — Smart-only via `visibility` on the section
   (`input_select.garden_irrigation_mode == Smart`):
   - Probe chips L / R / Sona (red below `start_pct`, else cyan).
   - Verdict chip (dynamic thresholds, plain-English why-drip).
   - `custom:expander-card` titled **Tuning**, collapsed by default, wrapping an
     `entities` card with the four sliders (`garden_drip_soil_start/_stop/_sat`,
     `garden_drip_min_days_between`).

4. **7-Day Schedule** (default span) — the existing `markdown` table card,
   unchanged content (mode-aware lawn/zones/drip + footnote).

5. **Irrigation Control** (default span) — mode select + one-off scheduler
   (`garden_oneoff_type` select, `garden_oneoff_at` datetime, Schedule/Cancel
   buttons). Pulled out of the old left column.

6. **Run Now** (default span) — the three run buttons (Lawn/Drip/Full) PLUS the
   minutes-per-zone slider and the Run-Lawn-now button, regrouped here (today
   they are split across columns).

7. **Pergola** (default span) — roof cover + weather mode select. Unchanged.

8. **Gates** (default span) — park gate + garage gate covers. Unchanged.

9. **Terrace** (default span) — door/porch chips. NOTE: these chips also appear
   in At-a-Glance. Decision: **At-a-Glance shows status only; the Terrace
   cluster is removed** to avoid duplication, since its chips were already
   status-only (no controls). Park/garage *covers* keep their full control
   cards in Gates; their At-a-Glance entries are status-only duplicates of the
   same entity, which is acceptable (glance vs. control are different
   affordances).

## Card mechanics / known gotchas

- **Masonry packing** requires each card inside a section to NOT force
  `grid_options: { columns: full }` unless it should span the section. Cards
  left at default width let HA flow them. (This is the inverse of the old
  single-section pattern, where every card needed `columns: full`.)
- **`visibility` on a whole section** is supported and is the clean way to make
  Soil & Drip Smart-only — avoids the mushroom mutually-exclusive-pair bug
  (no complementary sibling cards involved).
- **Expander card** is `custom:expander-card`; if the HACS resource is not
  loaded it renders as a `custom:expander-card` text placeholder. Playwright
  verification must confirm it renders as an actual accordion, not a stub.
- **Chips band length:** ~8 chips on one full-width band wraps fine on the
  landscape tablet; `alignment: justified` (matches existing chip cards).
- All Smart-drip templates already read `start_pct` / `stop_pct` from
  `sensor.garden_drip_soil_status` — no template changes needed, they move
  verbatim.

## Open Dependency

`lovelace-expander-card` is a HACS frontend resource the **user installs**
(HACS → Frontend → "Expander Card" → install; resource auto-registers as
`/hacsfiles/lovelace-expander-card/expander-card.js`). The implementation plan
assumes it is present.

**Fallback if not installed:** add `input_boolean.garden_show_tuning` (in the
garden `config.yaml`), a toggle chip in the Soil & Drip section, and gate the
slider `entities` card with `visibility` on that boolean. This is native, needs
no HACS, and matches existing repo visibility patterns — but is a touch less
slick than a real accordion. The plan will branch on whether the resource is
detected during verification.

## Verification

Per the `playwright-validate-dashboards` and `reload-after-push` knowledge
leaves:

1. Push to `chore/june-features` (HA currently tracks this branch).
2. Wait for pull; reload not needed for lovelace YAML, but force-refetch the
   config via WS (`lovelace/config`, `force: true`) to bypass frontend cache.
3. Navigate away and back to re-mount the view.
4. Full-page Playwright screenshot. Verify:
   - No dead whitespace band; masonry packs columns evenly.
   - At-a-Glance band renders all chips, no wrap clipping.
   - Soil & Drip section hidden when mode ≠ Smart, shown when Smart.
   - Expander renders as an accordion (collapsed), expands on tap to show the
     four sliders — NOT a `custom:` stub.
   - Run-Now buttons + minutes slider grouped together.
   - Covers (pergola/gates) controls still functional.
   - 0 console errors.
