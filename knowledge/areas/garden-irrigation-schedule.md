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

- **Day-of-week schedule logic is copied into 3 independent places.** Change one, the others silently disagree. All keyed on ISO weekday (`dow`): Mon=1 … Sun=7.
  1. `packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml` — `lawn_today` + `drip_today` attrs. Drives the actual `garden_scheduled_irrigation` automation (what runs).
  2. `packages/areas/outdoor/garden/templates/garden_next_run.yaml` — two near-identical blocks (lawn + drip next-run sensors).
  3. `dashboards/tablet/outdoor.yaml` — markdown card with its own `lawn_run`/`drip_run` Jinja macros for the 7-Day Schedule table.
- **Same edit, all 3.** Each encodes Smart-by-month + per-mode (Eco/Standard/Intensive/Testing) branches. Grep the per-mode pattern (e.g. `dow in [`, `dow ==`) across all three before claiming done.
- **README table** (`packages/areas/outdoor/garden/README.md`) also lists days per mode — human-facing, update for consistency.
- **profile + next_run are template sensors** → need `template.reload` after push. The **dashboard markdown card** is not a sensor — re-renders on view load, no reload, but frontend cache means Playwright verify (force-refetch + navigate away/back) is the only proof. See [reload-after-push].
- **Tiers differ by frequency, not just duration.** Eco 2×/wk `[2, 6]` (Tue/Sat), Standard 3×/wk `[2, 4, 6]` (Tue/Thu/Sat), Intensive 4×/wk `[1, 2, 4, 5]` (Mon/Tue/Thu/Fri). Testing daily; Off off. Each tier carries its own day set — there is no shared Tue/Fri default.
- **Durations: z1 longest, z2 = z3.** Eco/Standard 1800/1080/1080s, Intensive 2100/1200/1200s. The dashboard `lawn_total` macro hardcodes the per-tier sum (Eco/Std 3960, Int 4500) — a 4th place to update on a duration change.
- **Smart mode** auto-routes by month, inheriting each tier's *own* day set: May–Jun→Standard (`[2,4,6]`), Jul–Aug→Intensive (`[1,2,4,5]`), Sep→Eco (`[2,6]`), Oct→drip-only every-3-days (`yday % 3`, not weekday), Nov–Apr OFF.
- **profile + next_run compute the effective mode inline per attribute** — do NOT read a sibling attr via `this.attributes.get(...)`. Template-sensor attribute eval order / `this` staleness is unreliable, so each attr re-derives Smart's month→tier mapping itself. A read-only `effective_mode` attr exists for debug/dashboard, not as an input to the others.
