# CLAUDE.md

Home Assistant configuration for a smart home in Poland. Modular, package-based.

## Interacting with Home Assistant

Escalation order when querying or controlling HA:

1. **MCP tools** — `HassTurnOn`, `HassTurnOff`, `GetLiveContext`, `HassLightSet`, `HassClimateSetTemperature`, ha-config-analyzer (`find_entity_usages`, `analyze_automation`, `search_config`)
2. **`/cli` skill** — `hass-cli` for bulk state queries, entity registry, history
3. **`/api` skill** — REST/WebSocket via `curl`/`websocat` for registry updates, template rendering, event subscriptions
4. **Playwright** — last resort, only for UI-only or visual verification

When checking which entities exist, query the live HA instance (MCP / `hass-cli` / API) — do NOT rely on grepping this repo. Many entities come from integrations (Zigbee, MQTT, Satel, HACS) and aren't referenced in any YAML here.

## Commands

- Use `uv` for all Python tools (`uv run python script.py`, `uv run yamllint .`). Never `pip`/`pip3`.
- Run git commands from the working directory. Do NOT use `git -C <path>`.
- Lint: `uv run pre-commit run --all-files` (all hooks) or `uv run yamllint .` (YAML only).
- Recipes via `just`: `just lint`, `just check` (HA config check), `just push` (commit + push).
- Env vars (`$HA_URL`, `$HA_TOKEN`, `$API_ACCESS_TOKEN`) preloaded via direnv. `.env` reads/writes are hook-blocked — use the vars directly.

## Deployment

- HA auto-pulls the current git branch. Local edits are NOT live until pushed.
- **Never push to `main`.** Use a feature branch + PR.
- After every push, reload HA config (call `homeassistant.reload_core_config` service via MCP/API) and check logs — errors stay invisible until reload.
- Sandbox blocks `homeassistant.local`; curl against HA needs `dangerouslyDisableSandbox: true`.

## Architecture

Configuration is split into packages under `/packages/`:

- `areas/{floor}/{area}/` — per-room packages (floors: `ground-floor`, `first-floor`, `outdoor`)
- `areas/{floor}/_floor/` — floor-level aggregation (scripts, templates, lights)
- `bootstrap/` — core system config and templates (`bootstrap/templates/` for shared Jinja2 sensors)
- `frontend/`, `presence/`, `homekit/`, `energy/`, `misc/` — UI, occupancy logic, HomeKit, energy dashboards, miscellaneous helpers

Each area package has: `config.yaml`, `automations/`, `lights/`, `templates/`.

Entry point: `configuration.yaml`. Secrets in gitignored `secrets.yaml` (template: `secrets.fake.yaml`). Reusable automation templates in `blueprints/`.

`flight-tracker/` is a separate Python sub-project (own `uv` env, FastAPI + scheduler) running as an HA add-on. Recipes: `just ft-run`, `just ft-poll`, `just ft-download-data`.

## Knowledge layer

`knowledge/` is a frontmatter-routed how-to layer for **task-scoped** gotchas and procedures — the on-demand counterpart to the always-on rules in this file. Leaves are grouped into subdirectories (buckets) that the author creates as needed — not a fixed set. The generated `knowledge/INDEX.md` is one flat table (a row per leaf, columns from frontmatter) — never hand-edit between the markers; pre-commit rebuilds + re-stages it.

- **Recall:** invoke the `knowledge-router` skill before operational work — it matches intent against the INDEX table and loads matching leaves on demand. Re-route per task, not per session.
- **Capture:** a non-obvious gotcha or correction → invoke the `knowledge-author` skill (owns the relevance gate, dedup, frontmatter, rebuild, commit). Never patch leaves inline.

## Conventions

- Automation filenames: `{area}_{action}_{trigger}.yaml` with descriptive `alias` and unique `id`.
- New devices go in the matching area's `config.yaml`; update light groups/templates as needed.
- After adding/modifying an area package, run `/ha-area-docs` to regenerate its README.
- For automation patterns inside `packages/areas/**` (occupancy state machine, manual override + safety timeout), see `.claude/rules/area-patterns.md` — auto-loaded when editing area files.
- Lovelace dashboard URL keys (`lovelace.dashboards.<key>`) **must contain a hyphen** (e.g., `wall-tablet`). HA rejects config load otherwise.
- Dashboards live in `dashboards/{tablet,phone}.yaml`; each view is a separate `dashboards/{tablet,phone}/{view}.yaml` included from the entrypoint. Tablet `home.yaml` uses `sections` layout, `max_columns: 3`.
