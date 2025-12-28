# Home Assistant Configuration Tasks

# Push all changes with a standard commit message
push:
    git add .
    git commit -m "chore: changes"
    git push

# Validate YAML files
lint:
    yamllint .

# Check Home Assistant configuration (requires HA installed)
check:
    hass --config . --check-config
