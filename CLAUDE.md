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

## Architecture

Configuration is split into packages under `/packages/`:

- `areas/{floor}/{area}/` — per-room packages (floors: `ground-floor`, `first-floor`, `outdoor`)
- `areas/{floor}/_floor/` — floor-level aggregation (scripts, templates, lights)
- `bootstrap/` — core system config and templates (`bootstrap/templates/` for shared Jinja2 sensors)
- `frontend/`, `presence/`, `homekit/` — UI, occupancy logic, HomeKit integration

Each area package has: `config.yaml`, `automations/`, `lights/`, `templates/`.

Entry point: `configuration.yaml`. Secrets in gitignored `secrets.yaml` (template: `secrets.fake.yaml`). Reusable automation templates in `blueprints/`.

## Conventions

- Automation filenames: `{area}_{action}_{trigger}.yaml` with descriptive `alias` and unique `id`.
- New devices go in the matching area's `config.yaml`; update light groups/templates as needed.
- After adding/modifying an area package, run `/ha-area-docs` to regenerate its README.
- For automation patterns inside `packages/areas/**` (occupancy state machine, manual override + safety timeout), see `.claude/rules/area-patterns.md` — auto-loaded when editing area files.
