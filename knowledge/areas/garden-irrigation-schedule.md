---
summary: Garden irrigation day-of-week schedule logic is duplicated in 3 places — change all or the dashboard lies.
before_action:
  - About to change the garden irrigation schedule (days, frequency, durations)
  - About to edit garden_irrigation_profile or garden_next_run templates
on_symptom:
  - "garden 7-day schedule on tablet shows wrong days after a schedule change"
  - "irrigation next-run sensor disagrees with the dashboard forecast"
---

# Garden irrigation schedule

## Gotchas

- **Day-of-week schedule logic is copied into 3 independent places.** Change one, the others silently disagree. All keyed on ISO weekday (`dow`): Mon=1 … Sun=7.
  1. `packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml` — `lawn_today` + `drip_today` attrs. Drives the actual `garden_scheduled_irrigation` automation (what runs).
  2. `packages/areas/outdoor/garden/templates/garden_next_run.yaml` — two near-identical blocks (lawn + drip next-run sensors).
  3. `dashboards/tablet/outdoor.yaml` — markdown card with its own `lawn_run`/`drip_run` Jinja macros for the 7-Day Schedule table.
- **Same edit, all 3.** Each encodes Smart-by-month + per-mode (Eco/Standard/Intensive/Testing) branches. Grep the per-mode pattern (e.g. `dow in [`, `dow ==`) across all three before claiming done.
- **README table** (`packages/areas/outdoor/garden/README.md`) also lists days per mode — human-facing, update for consistency.
- **profile + next_run are template sensors** → need `template.reload` after push. The **dashboard markdown card** is not a sensor — re-renders on view load, no reload, but frontend cache means Playwright verify (force-refetch + navigate away/back) is the only proof. See [reload-after-push].
- **All weekday-scheduled modes run Tue/Fri** (`dow in [2, 5]`): Eco, Standard, Intensive, and Smart's May–Sep branches. Testing is daily; Off is off.
- **Smart mode** auto-routes by month: May–Jun→Standard params, Jul–Aug→Intensive, Sep→Eco params (Tue/Fri, 2×/wk), Oct→drip-only every-3-days (`yday % 3`, not weekday), Nov–Apr OFF.
