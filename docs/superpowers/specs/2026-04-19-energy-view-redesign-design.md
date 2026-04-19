# Energy View Redesign — Monthly Focus + Cost (PLN)

**Date:** 2026-04-19
**Scope:** `dashboards/tablet/energy.yaml`, `dashboards/phone/energy.yaml`, new file `packages/bootstrap/energy.yaml`

## Goal

Replace the current energy dashboards with a monthly-first view that answers two questions at a glance:

1. **How much electricity did I use / am I on track to use this month?**
2. **How much is that in PLN?**

Scope stays at the **plug-tracked devices only** — 11 Aqara/Zigbee light plugs plus washer and tumble dryer from the Hon integration. No whole-home meter is added in this redesign (recorded as a possible follow-up, not part of this work). There is no solar / grid / tariff integration; cost is a simple `kWh × rate` multiplication using a user-tunable rate helper.

## Non-goals

- No whole-home Shelly EM / Zigbee clamp install.
- No day/night (G12) tariff logic. Provider is PGE on a G11 flat tariff.
- No HA-native Energy settings page — would surface partial data without a grid sensor and mislead.
- No standing charges / fixed monthly fees in the cost number.
- Existing `sensor.*_energy` sensors are NOT migrated. The new `utility_meter`s read from them; originals remain.

## Tracked devices

Thirteen sources total. Three currently-unavailable sensors are deliberately excluded.

| Source sensor | Name on dashboard |
|---|---|
| `sensor.sypialnia_lazienka_energy` | Ensuite Bathroom |
| `sensor.kuchnia_ledy_energy` | Kitchen LEDs |
| `sensor.living_room_light_standing_lamp_energy` | Standing Lamp |
| `sensor.swiatlo_przed_domem_energy` | Porch |
| `sensor.main_bathroom_energy` | Bathroom |
| `sensor.wyspa_swiatla_energy` | Kitchen Island |
| `sensor.boiler_room_energy` | Boiler Room |
| `sensor.laundry_energy` | Laundry |
| `sensor.bedroom_reflectors_energy` | Bedroom Reflectors |
| `sensor.sypialnia_sonia_swiatlo_energy` | Bedroom Sona |
| `sensor.washer_energy` | Washer |
| `sensor.tumble_dryer_energy` | Tumble Dryer |

Excluded (unavailable at scan time 2026-04-19): `sensor.0x54ef441000ae4940_energy`, `sensor.syplazienka_lustro_energy`, `sensor.lazienka_glowna_lustro_energy`.

## Components

### A. Helper — `input_number.energy_tariff_rate`

Defined in `packages/bootstrap/energy.yaml`.

- Unit: `PLN/kWh`
- Min: `0.00`, Max: `3.00`, Step: `0.01`
- Initial: `1.00` (placeholder — user tunes from the UI once they check the PGE bill)
- Icon: `mdi:currency-eur` (or `mdi:cash`)
- Mode: `box`

### B. Monthly utility meters — one per tracked source

`utility_meter:` integration, one entry per source sensor. Cycle: `monthly`. Entities land as `sensor.<source>_monthly` — so `sensor.kuchnia_ledy_energy_monthly`, etc. These reset on the 1st of each month. HA persists the last cycle's total for statistics.

Consolidated in `packages/bootstrap/energy.yaml`.

### C. Template sensors — rollups

Also in `packages/bootstrap/energy.yaml`. Four sensors:

1. **`sensor.energy_tracked_month_kwh`** — `device_class: energy`, unit `kWh`. Sums the 13 `*_monthly` states with `| float(0)` guards.
2. **`sensor.energy_tracked_month_cost`** — `device_class: monetary`, unit `PLN`. `state: {{ states('sensor.energy_tracked_month_kwh') | float(0) * states('input_number.energy_tariff_rate') | float(1) }}` rounded to 2 dp.
3. **`sensor.energy_tracked_month_projected_kwh`** — `device_class: energy`, unit `kWh`. Linear projection: `month_kwh ÷ now().day × days_in_month`. Returns `unknown` on day 1.
4. **`sensor.energy_tracked_month_projected_cost`** — `device_class: monetary`, unit `PLN`. `projected_kwh × tariff_rate`, rounded to 2 dp.

Days-in-month computed via Jinja: `(now().replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)` → `.day`. Standard idiom; Python `calendar` module is not exposed in HA Jinja.

Per-device monthly cost is **not** materialized as a sensor — computed inline in the card template from `<source>_monthly × tariff_rate` to keep entity count down.

### D. Dashboard — tablet (`dashboards/tablet/energy.yaml`)

Layout: `type: sections`, `max_columns: 3`, one section with `column_span: 3`. Every card uses `grid_options: { columns: full }`.

**Row 1 — Hero (`horizontal-stack` of 3 Mushroom template cards):**

- `This Month` — primary `{{ month_kwh }} kWh · {{ month_cost }} PLN`, secondary `day {{ now().day }} of {{ days_in_month }}`, icon `mdi:lightning-bolt`, amber.
- `Projected` — primary `~{{ projected_kwh }} kWh · {{ projected_cost }} PLN`, secondary `at current pace`, icon `mdi:trending-up`, blue. Hidden (`visibility:`) when `now().day < 3` (noisy early in the month).
- `Rate` — primary `{{ states('input_number.energy_tariff_rate') }} PLN/kWh`, tap_action opens more-info on the `input_number` so the value can be edited in-place.

**Row 2 — Monthly trend:** `type: statistics-graph`, `period: month`, `days_to_show: 365`, `chart_type: bar`, `stat_types: [change]`, single entity `sensor.energy_tracked_month_kwh`'s source. Title: "Last 12 months".

**Row 3 — This month by device:** a `vertical-stack` of 13 Mushroom template cards (one per device). No static Top-5 / "rest" split — visual ranking comes from the bar inside each card.

- `primary`: device name
- `secondary`: `{{ kwh }} kWh · {{ kwh × tariff }} PLN`
- `card_mod` applies a horizontal gradient background: `linear-gradient(90deg, var(--amber) {{ pct }}%, transparent {{ pct }}%)` where `pct = this_device_kwh / max(all_device_kwh) × 100`. Tallest consumer = full bar; visibly smaller ones = proportional stubs.
- List order in YAML is alphabetical for stability. Visual ordering is driven purely by bar length, so the biggest consumer is always visually obvious regardless of list position.

This replaces the earlier "Top 5 + full list" approach — a single list with inline bars is simpler, avoids duplicating entities, and needs no manual re-sorting as consumption shifts month to month.

**Row 4 — Live power:** kept from the old dashboard, condensed. `type: entities` listing the `*_power` sensors for the same 13 devices. Title "Live power (W)".

### E. Dashboard — phone (`dashboards/phone/energy.yaml`)

Single column (`max_columns: 1`, natural stacking — no `column_span` tricks needed on phone). Card order:

1. **Hero** — one vertical Mushroom template card:
   - `primary`: `{{ month_kwh }} kWh · {{ month_cost }} PLN`
   - `secondary`: `This month · day {{ d }}/{{ dmax }} · on pace for {{ projected_cost }} PLN`
   - `layout: vertical`, icon `mdi:lightning-bolt`, amber.
2. **Rate chip** — small Mushroom card, `{{ rate }} PLN/kWh`, tap opens tariff helper.
3. **Monthly trend** — same `statistics-graph` as tablet.
4. **This month by device** — same single Mushroom+bar list as tablet row 3 (all 13 devices, visual ranking via gradient width).

No live-power row on phone. Phone energy is a "check my bill" view, not a real-time monitor.

### F. Removed from the old dashboards

- Weekly stacked bar chart (redundant with monthly).
- 180-day monthly stacked-per-device chart (unreadable — was the main complaint).
- All-time cumulative totals entity list (lifetime kWh without context is meaningless).
- Single-entity 24h sensor graph (not aligned with the monthly focus).

## Data flow

```
[13 Zigbee/Hon energy sensors]
          │
          ▼ (utility_meter, cycle: monthly, reset on 1st)
[13 *_monthly sensors]
          │
          ▼ (template sensor sum)
[sensor.energy_tracked_month_kwh]
          │         │
          │         ▼ (× input_number.energy_tariff_rate)
          │     [sensor.energy_tracked_month_cost]
          │         │
          │         ▼ (÷ days_elapsed × days_in_month)
          │     [sensor.energy_tracked_month_projected_cost]
          │
          ▼ (statistics-graph change/month, 365 days)
[Last-12-months bar chart]
```

## Error handling

- All templates use `| float(0)` on source states to survive briefly-unavailable sensors.
- `projected_cost` returns `unknown` on day 1 (`now().day == 1`) to avoid divide-by-zero; hero card hides the Projected tile with a `visibility:` condition when `now().day < 3`.
- `input_number.energy_tariff_rate` has `float(1)` fallback — multiplying by `1` leaves kWh unchanged rather than producing `0` if the helper is briefly unavailable during restart.

## Testing / verification

Per CLAUDE.md and `.claude/skills/ha-dashboards`:

1. `uv run pre-commit run --all-files` — YAML lint.
2. `git push` on branch; HA auto-pulls within 5–10 s.
3. Reload HA config (triggers template re-eval + utility_meter registration); tail logs for schema errors.
4. Playwright visual check on `/wall-tablet/energy` and `/mobile-phone/energy`. Full-width layout, three hero tiles on tablet, hero stack on phone, monthly bar chart renders, top-5 list shows kWh + PLN.
5. Tune `input_number.energy_tariff_rate` in the UI — hero cost value updates live.
6. Wait ≥1 cycle boundary (or manually reset one utility_meter via service call) to confirm the monthly reset works. This can't be fully verified in-session on 2026-04-19; acceptance is based on config validity + HA integration behavior being well-known.

## Open questions

None. All resolved during brainstorming:

- Scope = tracked plugs only (no whole-home meter).
- Tariff = G11 flat, rate stored in an `input_number` helper with placeholder `1.00`.
- Provider = PGE.
- Layout = current-month hero + history + per-device breakdown.
- Devices in breakdown = all 13 in a single list, each row showing an inline bar whose length = that device's share of the current month's top consumer.
- Targets = both tablet and phone dashboards.

## Risks / notes

- If `utility_meter` registration fails for a source sensor that is `unknown` at HA start, HA logs a warning but continues. The rollup sensor will skip that entity via the `float(0)` fallback. No user-facing breakage.
- The sum rollup treats all kWh as additive across ~13 plugs. Devices plugged behind the same plug are not double-counted because there's only one plug per device. The total is **not** the house total — it's the tracked-devices total. Hero subtitle should make this implicit ("Tracked devices this month") if ambiguity bites in practice; v1 ships without that clarifier and we revisit if confused.
- Adding or removing a tracked device in the future requires touching three places in `packages/bootstrap/energy.yaml` (utility_meter + sum template + device list on dashboards). Acceptable — device set rarely changes.
