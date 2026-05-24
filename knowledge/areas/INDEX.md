# areas/

<!-- LEAVES:START -->
- [garden-irrigation-schedule](garden-irrigation-schedule.md) — Garden irrigation day-of-week schedule logic is duplicated in 3 places — change all or the dashboard lies.
  - **before**: About to change the garden irrigation schedule (days, frequency, durations); About to edit garden_irrigation_profile or garden_next_run templates
  - **symptom**: garden 7-day schedule on tablet shows wrong days after a schedule change; irrigation next-run sensor disagrees with the dashboard forecast
- [occupancy-state-machine](occupancy-state-machine.md) — Area automation patterns (occupancy, manual override + safety timeout) live in a rules file.
  - **before**: About to add or edit an automation in an area package; About to wire occupancy or presence lighting for a room
  - **symptom**: manual light change gets stomped by an automation; occupancy lighting flickers or won't latch
<!-- LEAVES:END -->
