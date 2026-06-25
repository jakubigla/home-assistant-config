---
summary: Edge-triggered occupancy latch goes stale-OFF if its sensor is already ON across a reload; add a startup-sync branch.
before_action:
  - About to build or edit an input_boolean occupancy/presence latch on off->on edges
  - About to rely on a state-machine latch surviving an HA restart or reload
on_symptom:
  - "occupancy latch reads off while the room is clearly occupied after a restart or automation reload"
  - "presence-driven lights don't arm after HA restart even though the mmWave sensor shows on"
  - "watchdog clears a stuck-on latch but a stuck-off latch never self-corrects"
---

**An edge-triggered occupancy latch (`off->on` = entry, `off for X` = exit) misses the case where
the source sensor is already `on` when HA restarts or automations reload — no edge fires, so the
latch stays stale-`OFF` while the room is occupied.** The duration watchdog only clears stuck-`ON`;
it cannot fix stuck-`OFF`. (Surfaced live building `bedroom_occupancy_state_machine` — `bedroom_occupancy`
was steady `on` across a reload and `input_boolean.bedroom_occupied` never armed.)

**Fix: add a `sync` branch triggered on `homeassistant.start` + `automation_reloaded` that
re-derives the latch from current sensor states** — any source sensor `on` -> `turn_on`, else
`turn_off`. The resulting latch `off->on` edge re-fires downstream lighting automations, which keep
their own gates (e.g. a `sleeping_time` check still blocks auto-on at night).

```yaml
trigger:
  - trigger: homeassistant
    event: start
    id: sync
  - trigger: event
    event_type: automation_reloaded
    id: sync
# ...entry / exit / watchdog triggers...
action:
  - choose:
      - conditions: [{condition: trigger, id: sync}]
        sequence:
          - if:
              - condition: or
                conditions:
                  - {condition: state, entity_id: binary_sensor.SENSOR_A, state: "on"}
                  - {condition: state, entity_id: binary_sensor.SENSOR_B, state: "on"}
            then: [{action: input_boolean.turn_on, target: {entity_id: input_boolean.LATCH}}]
            else: [{action: input_boolean.turn_off, target: {entity_id: input_boolean.LATCH}}]
```

`ensuite_occupancy_state_machine` uses the same latch pattern and has the same gap — apply the sync
branch there too if restart-staleness ever matters for it.
