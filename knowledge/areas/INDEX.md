# areas/

<!-- LEAVES:START -->
- [garden-irrigation-schedule](garden-irrigation-schedule.md) — Garden irrigation day/duration logic is duplicated across 3 files (4 spots) — change all or the dashboard lies.
  - **before**: About to change the garden irrigation schedule (days, frequency, durations); About to edit garden_irrigation_profile or garden_next_run templates
  - **symptom**: garden 7-day schedule on tablet shows wrong days after a schedule change; irrigation next-run sensor disagrees with the dashboard forecast
- [occupancy-state-machine](occupancy-state-machine.md) — Area automation patterns (occupancy, manual override + safety timeout) live in a rules file.
  - **before**: About to add or edit an automation in an area package; About to wire occupancy or presence lighting for a room
  - **symptom**: manual light change gets stomped by an automation; occupancy lighting flickers or won't latch
- [script-call-blocks-automation](script-call-blocks-automation.md) — Calling a script as an automation action blocks until it finishes — use script.turn_on to fire-and-forget.
  - **before**: About to call a long-running script from an automation and run steps after it; About to clear a flag or set state after triggering an irrigation/sequence script
  - **symptom**: automation stuck at current=1 for the whole duration of a script it called; post-script step (clearing an input_boolean, notifying) only runs after the long run ends
<!-- LEAVES:END -->
