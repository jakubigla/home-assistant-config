
## Period: DAILY (last 24 hours)

Focus on things that went wrong or misbehaved today:

- New errors/warnings in the error log and system log. Group by integration; ignore known noise that
  recurs unchanged and has no effect.
- Automation traces with errors, `condition` aborts that look wrong, runs that hit timeouts, or
  automations that fired many times in a burst (flapping, loops, race with manual override).
- Lights/covers/climate that ended in a state contradicting their automation intent (e.g. light left on
  in an empty room overnight, presence stuck, manual-override never released).
- Entities `unavailable`/`unknown` for long stretches, and templates that render errors.
- Repairs and add-on/host health (OOM, restarts).

Keep daily changes tiny: at most 2 commits, only for clear bugs with direct evidence from today.
Everything else goes in the report.
