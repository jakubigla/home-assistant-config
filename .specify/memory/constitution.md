<!--
SYNC IMPACT REPORT
==================
Version Change: N/A → 1.0.0 (Initial constitution)
Bump Rationale: MAJOR - Initial creation of project constitution

Modified Principles: N/A (new document)

Added Sections:
- Core Principles (6 principles)
- Quality Standards
- Development Workflow
- Governance

Removed Sections: N/A

Templates Requiring Updates:
- .specify/templates/plan-template.md: ✅ No updates needed (generic template)
- .specify/templates/spec-template.md: ✅ No updates needed (generic template)
- .specify/templates/tasks-template.md: ✅ No updates needed (generic template)

Follow-up TODOs: None
-->

# Home Assistant Configuration Constitution

## Core Principles

### I. Invisible Automation (NON-NEGOTIABLE)

The best smart home is one where residents forget it's "smart." Automation MUST anticipate
needs and act without requiring user intervention for daily living.

- Automations MUST work silently in the background without app interaction
- Physical controls (switches, buttons) MUST always be available as overrides
- Manual override states MUST be respected until explicitly cleared or timed out
- Guest usability: The home MUST function for visitors without explanation
- Success metric: Residents do not think about automation; it just works

**Rationale**: A smart home that requires constant attention defeats its purpose. The goal
is enhanced living, not technology management.

### II. Reliability First

A failing smart home is worse than no automation at all. Reliability MUST take precedence
over adding new features or capabilities.

- Core functions (lights, climate, security) MUST work even when automation fails
- Physical switches MUST control lights regardless of network or software state
- Graceful degradation MUST be implemented: when sensors fail, use safe defaults
- All automations MUST be validated via CI/CD pipeline before deployment
- New features MUST NOT destabilize existing, working automations

**Rationale**: Family trust in the smart home depends on consistent reliability. One failed
automation erodes confidence in the entire system.

### III. Predictable Behavior

Users build mental models of how their home responds. Automation MUST be deterministic
and match user expectations consistently.

- Same trigger conditions MUST produce the same result every time
- All automation logic MUST be explainable in plain language
- No "magic" behaviors: every action must trace to a clear trigger/condition
- State changes MUST be visible in Home Assistant UI for debugging
- Edge cases MUST be documented in YAML comments or automation descriptions

**Rationale**: Unpredictable automation causes frustration and leads to disabled features.
Predictability builds trust and enables troubleshooting.

### IV. Local-First Processing

Smart home data is sensitive. Core automation MUST run locally without cloud dependencies.

- All essential automations MUST function during internet outages
- Cloud services MAY enhance functionality but MUST NOT be required for core features
- Sensitive data (presence, routines, camera feeds) MUST stay local by default
- External integrations MUST be explicitly justified and documented
- Network isolation SHOULD be supported for security-conscious deployments

**Rationale**: Cloud outages should not turn off your lights. Privacy and availability
require local processing as the foundation.

### V. Modular Architecture

Configuration MUST be organized into self-contained, reusable packages that can be
added, removed, or modified independently.

- Each physical area MUST have its own package under `/packages/areas/`
- Cross-area dependencies MUST be minimized and explicitly documented
- Shared functionality MUST reside in `/packages/bootstrap/` or dedicated packages
- Automations MUST follow naming convention: `{area}_{action}_{trigger}.yaml`
- New areas MUST be addable without modifying existing area packages

**Rationale**: Modular design enables incremental development, easier debugging, and
configuration reuse across deployments.

### VI. Maintainability & Simplicity

Complex automations are difficult to debug and maintain. Prefer simple, focused solutions.

- Each automation SHOULD have a single, clear purpose
- YAML files MUST pass linting (`yamllint`) before commit
- Configuration MUST be version controlled with meaningful commit messages
- Common patterns (presence detection, manual override) MUST be documented in CLAUDE.md
- Complexity MUST be justified; default to the simplest working solution

**Rationale**: A maintainable configuration survives over years. Clever solutions become
technical debt when debugging at 2 AM.

## Quality Standards

### Configuration Validation

- All YAML MUST pass `yamllint` with the project's `.yamllint` configuration
- Home Assistant configuration MUST validate successfully in CI/CD
- Breaking changes MUST be tested in a development environment before deployment

### Testing Approach

- Critical automations SHOULD be tested via Home Assistant's trace/debug tools
- Presence detection logic SHOULD be validated with real-world scenarios
- New integrations SHOULD be tested for failure modes (offline, timeout, error responses)

### Documentation Requirements

- Area packages MUST include descriptive comments for non-obvious logic
- CLAUDE.md MUST document recurring patterns and architectural decisions
- Secrets MUST be documented in `secrets.fake.yaml` as a template

## Development Workflow

### Change Process

1. Create feature branch for non-trivial changes
2. Make changes following modular architecture principles
3. Validate YAML linting locally: `yamllint .`
4. Test automation behavior in Home Assistant development mode
5. Push to trigger CI/CD validation
6. Merge only after pipeline passes

### Code Review Focus Areas

- Reliability: Does this automation fail gracefully?
- Predictability: Will users understand what this does?
- Simplicity: Is there a simpler approach?
- Modularity: Does this belong in the correct package?

### Deployment

- Configuration updates deploy automatically upon push to main branch
- Breaking changes SHOULD be communicated to household members
- Rollback capability MUST be maintained via git history

## Governance

This constitution defines the guiding principles for all development on this Home Assistant
configuration. Deviations require explicit justification and documentation.

### Amendment Process

1. Propose amendment with rationale in a pull request
2. Document impact on existing automations
3. Update version number following semantic versioning:
   - MAJOR: Principle removal or fundamental redefinition
   - MINOR: New principle or significant expansion
   - PATCH: Clarification or wording improvements
4. Update CLAUDE.md if development patterns change

### Compliance

- All pull requests SHOULD verify adherence to core principles
- Principle violations MUST be documented with justification in PR description
- Periodic review of automations against principles is encouraged

### Reference

For runtime development guidance and common patterns, refer to `CLAUDE.md` at repository root.

**Version**: 1.0.0 | **Ratified**: 2025-12-28 | **Last Amended**: 2025-12-28
