---
summary: Silent Z2M battery sensors stay stale, never unavailable; detect by max(last_updated), clear latch on full recovery.
before_action:
  - About to build a watchdog or staleness check for a battery Zigbee2MQTT sensor
  - About to clear a once-per-day alert latch on a device reporting again
on_symptom:
  - "soil/temp/battery sensor shows a value but it never updates / is stale"
  - "device went quiet after a restart but entity still shows the old reading"
  - "silent-probe / offline watchdog floods notifications, fires every cycle not once a day"
  - "unavailable-state check never catches a sensor that stopped reporting"
---

# Z2M battery sensor silence — detect by age, latch on full recovery

## Battery Z2M sensors don't go unavailable when silent

- **A silent battery Zigbee2MQTT sensor keeps showing its last value — it does NOT go
  `unavailable`.** On any broker/Z2M/host restart (e.g. an HA OS update reboot), Z2M republishes
  the device's retained MQTT payload on reconnect, so the entity "updates" to the same stale
  reading while the physical device has said nothing. A state-based check (`state == 'unavailable'`)
  never fires. Sleepy end devices that fail to re-check-in after the coordinator restarts look
  identical to healthy ones by state alone. (Surfaced when `sona_flowerbed` sat silent for hours
  post-reboot at a cached 97% while siblings reported every ~20-30 min.)
- **Detect silence by AGE, not state:** take `max(last_updated)` across all the device's channels
  (temperature, soil_moisture, illuminance, battery) and compare to a cutoff (`now - 2h`). The
  newest channel is the real "last heard from device"; moisture alone is misleading (it changes
  slowly, so a long gap is normal). See `garden_soil_probe_silent_watchdog.yaml`.

## A latched once-per-day alert must clear on FULL recovery, not any-entity report

- **When one device is silent but healthy siblings report every cycle, a reset that clears the alert
  latch on ANY monitored entity reporting will re-fire the alert every watchdog cycle — a flood.**
  The fix: gate the latch-clear so it only fires when NO monitored device is still silent
  (re-evaluate the same `max(last_updated)` test; clear only if the silent list is empty). A
  neighbour's report then can't disarm the latch while the real problem persists, so the alert stays
  at most once per day (latch clears on true recovery or at midnight). See
  `garden_soil_probe_silent_reset.yaml`.

## Note

- Distinct from [[tuya-local-sprinkler-zombie]] — that is the mains tuya_local valve CONTROLLER
  going `unavailable` on DHCP IP drift. This is battery Z2M leaf sensors going silent-but-available.
