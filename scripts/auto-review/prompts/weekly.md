
## Period: WEEKLY (last 7 days)

Look for patterns a single day cannot show:

- Automations by run count: never fired all week (dead/obsolete or broken trigger), fired excessively
  (noisy trigger, missing debounce `for:`), or frequently ending via safety timeout (override logic
  not releasing normally).
- Repeated manual corrections: user switches a light/cover/thermostat right after an automation acts,
  consistently at similar times/conditions. That means the automation's thresholds/timing are wrong.
  Propose a tuned threshold with the numbers that support it.
- Presence/occupancy false positives/negatives; lux/darkness thresholds that disagree with real use.
- Recurring error-log entries, slow or failing traces, unavailable entities per device with timing
  (Zigbee: LQI, offline flapping), battery levels trending below 20%.
- Energy and climate: unusual consumption vs. previous week, heating that runs against open windows,
  standby draw.
- Helpers/entities defined in the repo but unused, or referenced entities that no longer exist
  (use ha-config-style grep over the repo against the live registry).

Up to 4 commits, each one independent and individually revertible. Prefer fixes with a measurable
before/after you can state in the PR body.
