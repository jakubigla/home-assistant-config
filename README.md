# Home Assistant Configuration

[![Home Assistant CI](https://github.com/jakubigla/home-assistant-config/actions/workflows/home-assistant.yml/badge.svg)](https://github.com/jakubigla/home-assistant-config/actions/workflows/home-assistant.yml)

Smart home configuration for a house in Poland, just outside of Warsaw. Built with a modular, package-based architecture for maintainability and scalability.

## Dashboard

![Tablet Dashboard](docs/images/tablet-dashboard.png)

## Architecture

The configuration uses a **package-based organization** where each physical area and functional domain has its own isolated package:

```text
packages/
├── areas/               # Physical locations, organized by floor
│   ├── ground-floor/
│   │   ├── _floor/      # Floor-level aggregation (scripts, templates, lights)
│   │   ├── kitchen/
│   │   ├── living-room/
│   │   ├── toilet/
│   │   ├── vestibule/
│   │   └── boiler-room/
│   ├── first-floor/
│   │   ├── bedroom/
│   │   ├── bathroom/
│   │   ├── hall/
│   │   └── laundry/
│   └── outdoor/
│       ├── porch/
│       └── terrace/
├── bootstrap/           # Core system configurations and templates
├── frontend/            # UI customizations and themes
├── homekit/             # Apple HomeKit integration
├── misc/                # Cross-area automations
└── presence/            # Occupancy detection logic
```

### Area Package Structure

Each area follows a consistent structure:

```text
packages/areas/{floor}/{area}/
├── config.yaml      # Main area configuration
├── automations/     # Area-specific automations
├── lights/          # Light group configurations
└── templates/       # Dynamic sensors and binary sensors
```

### Design Principles

| Principle | Description |
|-----------|-------------|
| **Invisible Automation** | Automations work seamlessly without manual intervention |
| **Reliability First** | Prefer robust solutions over complex ones |
| **Predictable Behavior** | Users can anticipate how the system will respond |
| **Local-First** | Minimize cloud dependencies |
| **Modular Architecture** | Each area is self-contained with clear boundaries |
| **Maintainability** | Simple, readable configurations |

## Key Features

- **Presence Detection**: Multi-sensor Bayesian probability for accurate occupancy
- **Adaptive Lighting**: Automatic control based on occupancy, time, and ambient light
- **Manual Override Pattern**: Physical switches override automation with safety timeouts
- **Movie Mode**: Explicit toggle for dark-room scenarios in bedroom
- **Cross-Area Control**: Cube controller for multi-room operations

## Areas

| Floor | Areas |
|-------|-------|
| Ground Floor | Living Room, Kitchen, Toilet, Vestibule, Boiler Room |
| First Floor | Bedroom (with Ensuite), Bathroom, Hall, Laundry |
| Outdoor | Porch, Terrace |

## Development

### Prerequisites

- [uv](https://docs.astral.sh/uv/) - Python package manager
- [Home Assistant](https://www.home-assistant.io/) (for testing)

### Setup

```bash
# Install dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
```

### Pre-commit Hooks

The following hooks run automatically on commit:

| Hook | Purpose |
|------|---------|
| `yamllint` | YAML linting (matches CI configuration) |
| `check-yaml` | YAML syntax validation |
| `trailing-whitespace` | Remove trailing whitespace |
| `end-of-file-fixer` | Ensure files end with newline |
| `detect-secrets` | Prevent committing credentials |
| `no-commit-to-branch` | Block direct commits to main |
| `conventional-pre-commit` | Enforce conventional commit format |
| `markdownlint` | Markdown linting |
| `shellcheck` | Shell script linting |

Run hooks manually:

```bash
uv run pre-commit run --all-files
```

### Linting

```bash
# YAML linting
uv run yamllint .

# Or use pre-commit
uv run pre-commit run yamllint --all-files
```

### Naming Conventions

- **Automations**: `{area}_{action}_{trigger}.yaml`
- **Templates**: Organized in subdirectories by type (`binary_sensors/`, `sensors/`)
- **Entities**: Follow Home Assistant naming standards

### Adding a New Automation

1. Place in the appropriate area: `packages/areas/{floor}/{area}/automations/`
2. Follow naming convention: `{area}_{action}_{trigger}.yaml`
3. Include descriptive `alias` and unique `id`
4. Run `uv run yamllint` to validate

### Cross-Area Automations

Automations that control entities across multiple areas belong in `packages/misc/`:

```yaml
# packages/misc/automations/misc_{name}.yaml
alias: "Misc - Descriptive Name"
description: "Controls cross-area entities (list affected areas)"
```

## CI/CD

GitHub Actions automatically validates on push:

- **yamllint**: YAML syntax and style
- **remarklint**: Markdown formatting
- **Home Assistant**: Configuration validation

## Secrets

Real secrets are stored in `secrets.yaml` (gitignored). Use `secrets.fake.yaml` as a template for required secrets.
