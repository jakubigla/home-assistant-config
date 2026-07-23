---
summary: float/int filter defaults don't catch UndefinedError — missing dict keys need .get(); Met.no drops uv_index past day 3.
before_action:
  - About to read keys off a weather.get_forecasts or other service-response dict in a template
  - About to rely on `| float(default)` / `| int(default)` to guard a possibly-missing dict key
on_symptom:
  - "UndefinedError: 'dict object' has no attribute"
  - "Error rendering attributes.<attr> template for sensor.<x> (attribute missing while state looks fine)"
  - "forecast/heat-tier attribute empty or stale while near-day values render"
---

# Jinja float/int defaults don't guard missing dict keys

- **`x.missing_key | float(0)` RAISES UndefinedError — the default never applies.** HA's forgiving
  float/int filters catch ValueError/TypeError only; a missing dict attribute is a Jinja
  UndefinedError and propagates, killing the WHOLE template render (one bad key on one loop item =
  the entire attribute renders nothing). Guard raw-dict reads with `day.get('key', 0) | float(0)`
  (or `| default(0)` before the cast). Bites raw dicts only — service responses, parsed JSON,
  `trigger.to_state.attributes`; `states()`/`state_attr()` helpers are unaffected.
- **Met.no daily `weather.get_forecasts` omits `uv_index` beyond ~day 3** (temperature/condition
  present on all days). Any per-day loop reading `day.uv_index` dies on day 4+ — killed
  `sensor.garden_forecast_today`'s `forecast_7day` silently for weeks (36 log occurrences; future
  heat tiers fell back to Mild). The trigger-based sensor kept its last good state, so dashboards
  looked alive — only the system log showed it.
- Prove either form cheaply via `/api/template` with a literal dict:
  `{% set d = {'a': 1} %}{{ d.b | float(0) }}` errors; `{{ d.get('b', 0) | float(0) }}` → `0.0`.
