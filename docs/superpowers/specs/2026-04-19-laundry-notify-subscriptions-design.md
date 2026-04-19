# Laundry notification subscriptions — design

**Date:** 2026-04-19
**Status:** Approved, ready for implementation planning

## Goal

Let the user subscribe to mobile push notifications when the washer or dryer finishes a cycle, controlled from the Appliances dashboard. Each appliance has its own subscription with two dimensions:

- **Mode:** `off` | `one_cycle` | `always`
- **Recipient:** `me` | `sona` | `both`

A convenience "Set both" control lets the user set washer + dryer mode together in one tap.

## Non-goals

- Smart cycle detection (debouncing power dips, cycle-duration floors, integration-specific "cycle complete" signals). The first iteration trusts raw `binary_sensor.*_power` `on → off` transitions; upgrade path is documented below.
- Presence-based recipient routing ("whoever is home"). Recipient is an explicit selector.
- Phone home-view shortcuts. Controls live on the Appliances tab only.
- Actionable notifications (buttons like "Snooze"/"Unloaded"). Plain title + body for now.

## Context

- Existing entities: `binary_sensor.washer_power`, `binary_sensor.tumble_dryer_power` — already on/off from power monitoring.
- Existing notify targets: `notify.mobile_app_iglofon_new` (user), `notify.mobile_app_iphone_uzivatela_sona` (Sona).
- Existing dashboard: `dashboards/tablet/appliances.yaml` — washer/dryer chips on home view; dedicated Appliances tab exists.
- Package home: `packages/areas/first-floor/laundry/` — currently only handles occupancy-driven lights. Extended here on conceptual grounds (laundry domain), even though the appliances may physically live elsewhere.

## Architecture

### File layout

```
packages/areas/first-floor/laundry/
├── config.yaml                              # extended: include helpers/ and scripts/
├── helpers/
│   └── notify_subscriptions.yaml            # NEW — 4 input_selects
├── scripts/
│   └── set_both_laundry_notify.yaml         # NEW — combined-control convenience
└── automations/
    ├── laundry_room_lights_on_when_occupied.yaml  # existing, untouched
    ├── washer_notify_on_finish.yaml         # NEW
    └── dryer_notify_on_finish.yaml          # NEW
```

Dashboard:
- `dashboards/tablet/appliances.yaml` — add a "Notifications" section.

### State model — HA helpers

Four `input_select` helpers:

| Entity                                   | Options                  | Initial | Purpose                                  |
| ---------------------------------------- | ------------------------ | ------- | ---------------------------------------- |
| `input_select.washer_notify_mode`        | off / one_cycle / always | off     | When to notify for washer                |
| `input_select.dryer_notify_mode`         | off / one_cycle / always | off     | When to notify for dryer                 |
| `input_select.washer_notify_recipient`   | me / sona / both         | me      | Who gets washer notifications            |
| `input_select.dryer_notify_recipient`    | me / sona / both         | me      | Who gets dryer notifications             |

Recipient is stored independently of mode — lets the user pre-configure "when I enable it, send to X" without changing modes.

**YAML gotcha:** In `input_select` option lists and `state:` comparisons, `off` must be quoted (`"off"`) — unquoted, YAML parses it as boolean `false`. Applies to all helpers and all automation/script references.

### Automations — per appliance

Two automations, one per appliance. Washer shape (dryer is identical with entity + name swaps):

```yaml
alias: Washer notify on finish
id: washer_notify_on_finish
mode: single

trigger:
  - platform: state
    entity_id: binary_sensor.washer_power
    from: "on"
    to: "off"

condition:
  - condition: not
    conditions:
      - condition: state
        entity_id: input_select.washer_notify_mode
        state: "off"

action:
  - choose:
      - conditions:
          - condition: state
            entity_id: input_select.washer_notify_recipient
            state: me
        sequence:
          - action: notify.mobile_app_iglofon_new
            data: &payload
              title: "Washer finished"
              message: "Time to unload the washer."
      - conditions:
          - condition: state
            entity_id: input_select.washer_notify_recipient
            state: sona
        sequence:
          - action: notify.mobile_app_iphone_uzivatela_sona
            data: *payload
      - conditions:
          - condition: state
            entity_id: input_select.washer_notify_recipient
            state: both
        sequence:
          - action: notify.mobile_app_iglofon_new
            data: *payload
          - action: notify.mobile_app_iphone_uzivatela_sona
            data: *payload

  - if:
      - condition: state
        entity_id: input_select.washer_notify_mode
        state: one_cycle
    then:
      - action: input_select.select_option
        target:
          entity_id: input_select.washer_notify_mode
        data:
          option: "off"
```

### "One cycle" semantics

Arms for the next `on → off` transition regardless of current appliance state.

- **Idle when armed:** waits for a cycle to run and finish, then notifies, then auto-disarms.
- **Running when armed:** fires at end of current cycle, then auto-disarms.

### Combined "Set both" control

A script that writes both appliances' mode in a single tap, leaving recipients untouched:

```yaml
set_both_laundry_notify:
  alias: Set both laundry notify
  fields:
    mode:
      selector:
        select:
          options: [off, one_cycle, always]
  sequence:
    - action: input_select.select_option
      target:
        entity_id:
          - input_select.washer_notify_mode
          - input_select.dryer_notify_mode
      data:
        option: "{{ mode }}"
```

(Option values in the `selector` list must be quoted in real YAML per the gotcha above.)

### Dashboard — Appliances tab "Notifications" section

Layout (always visible, no conditional gating):

```
┌───────────────────── Notifications ─────────────────────┐
│  Washer                                                  │
│    [ Off | One cycle | Always ]                          │
│    Recipient: [ Me | Sona | Both ]                       │
│                                                          │
│  Dryer                                                   │
│    [ Off | One cycle | Always ]                          │
│    Recipient: [ Me | Sona | Both ]                       │
│                                                          │
│  Set both:  [ Off ]   [ One cycle ]   [ Always ]         │
└──────────────────────────────────────────────────────────┘
```

Cards:
- **Per-appliance mode & recipient** → `mushroom-select-card` bound to each `input_select`. Native segment UI; no custom state logic.
- **Set both** → three `mushroom-template-card` buttons calling `script.set_both_laundry_notify` with `{mode: off | one_cycle | always}`.

## Edge cases & known limitations

- **False `on → off` blip during a cycle.** With raw transition detection (explicit decision in brainstorm), a brief power dip fires an early notify. Under `one_cycle`, the subscription silently disarms on the false trigger. Accepted trade-off for simplicity; upgrade path = replace trigger with a `for: "00:03:00"` state change or a debounced template binary sensor.
- **Automation `mode: single`.** A second `on → off` while the action is mid-flight is dropped. Acceptable — the cycle-end event is idempotent enough and the action completes in seconds.
- **Recipient changed mid-action.** `choose` evaluates at action time, so changing the recipient selector between trigger and action is honoured. No race to worry about.

## Verification plan

After implementation, validate:

1. YAML lint and HA config check pass.
2. Helpers appear in HA with correct options and initials.
3. Toggling each `input_select` from dashboard writes state correctly (Playwright visual check on Appliances tab).
4. Manually flip `binary_sensor.washer_power` via Developer Tools `on → off`:
   - Mode `off` → no notify.
   - Mode `always`, recipient `me` → notify iPhone only.
   - Mode `always`, recipient `both` → both phones notified.
   - Mode `one_cycle`, recipient `sona` → Sona notified, then selector resets to `off`.
5. Repeat for dryer.
6. "Set both" buttons → both mode selectors update in one tap; recipients unchanged.

## Future work (out of scope)

- Debounced finish detection (Q2 option A/B).
- Actionable notification with "Unloaded" button that also resets any `always` mode.
- Presence-aware recipient routing.
- History card on dashboard showing last N cycle finishes.
