
## Period: MONTHLY (last 30 days)

Strategic pass. Use history/statistics to see trends and seasonality:

- Config hygiene: dead or duplicated automations, copy-pasted logic that should be a blueprint or
  shared template, stale helpers, orphaned entities in the registry, disabled-but-referenced entities,
  deprecated syntax or integrations flagged in the logs/repairs (check the HA version in `get /api/config`
  against release notes you can infer from warnings).
- Seasonality: thresholds, schedules, sunrise/sunset offsets, heating/irrigation/pergola logic that
  drifted as days shorten or lengthen; propose seasonal adjustments backed by 30-day data.
- Reliability trends: devices whose availability or battery degraded week over week, add-on/host
  resource trends (this box has ~1.9 GB RAM; OOM kills are a known risk), recorder DB growth, entities
  with excessive state-write rates that should be excluded from recorder.
- Energy: monthly consumption and cost-shape changes, biggest consumers, standby load.
- Docs: area READMEs that no longer match their packages (follow `.claude/skills/ha-area-docs`
  guidance if you regenerate one).
- Re-review any recurring "Ideas not acted on" from prior months in `@@OUT@@/prior_prs.txt` context.

Up to 6 commits, grouped logically. Include a "Month in review" section at the top of the PR body:
3 to 6 bullet points on the health of the house.
