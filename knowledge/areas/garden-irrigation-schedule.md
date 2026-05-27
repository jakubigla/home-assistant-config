---
summary: Garden irrigation day/duration logic is duplicated across 3 files (4 spots) — change all or the dashboard lies.
before_action:
  - About to change the garden irrigation schedule (days, frequency, durations)
  - About to edit garden_irrigation_profile or garden_next_run templates
on_symptom:
  - "garden 7-day schedule on tablet shows wrong days after a schedule change"
  - "irrigation next-run sensor disagrees with the dashboard forecast"
---

# Garden irrigation schedule

## Gotchas

- **Schedule logic is copied into 4 spots — change all or the dashboard lies.** All keyed on ISO weekday (`dow`, Mon=1…Sun=7). Grep the per-mode pattern (`dow in [`, `dow ==`) across all before claiming done:
  1. `templates/garden_irrigation_profile.yaml` — `lawn_today`/`drip_today` attrs; drives the `garden_scheduled_irrigation` automation (what runs).
  2. `templates/garden_next_run.yaml` — two near-identical blocks (lawn + drip next-run sensors).
  3. `dashboards/tablet/outdoor.yaml` — markdown card, own `lawn_run`/`drip_run` macros for the 7-Day table; `lawn_total` macro hardcodes the per-tier duration sum (Eco/Std 3960, Int 4500).
  4. `packages/areas/outdoor/garden/README.md` — days-per-mode table, human-facing.
- **Tiers differ by frequency, each carries its own day set** (no shared default): Eco 2×/wk `[2,6]`, Standard 3×/wk `[2,4,6]`, Intensive 4×/wk `[1,2,4,5]`, Testing daily, Off off. Durations z1>z2=z3: Eco/Std 1800/1080/1080s, Int 2100/1200/1200s.
- **Smart auto-routes by month, inheriting each tier's own days:** May–Jun→Standard, Jul–Aug→Intensive, Sep→Eco, Oct→drip-only every-3-days (`yday % 3`, not weekday), Nov–Apr OFF.
- **Each attr re-derives Smart's month→tier mapping inline — never read a sibling attr** via `this.attributes.get(...)` (template-sensor eval order / `this` staleness unreliable). `effective_mode` is debug-only output, not an input.
- **Profile + next_run are template sensors** → `template.reload` after push. The dashboard markdown card is not a sensor (re-renders on view load) — frontend cache means Playwright force-refetch is the only proof. See **reload-after-push**, **playwright-validate-dashboards**.
