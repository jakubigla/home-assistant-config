# Claude Command: Zigbee Debug

Debug Zigbee devices in Home Assistant by analyzing the repository configuration and using browser automation to inspect Zigbee2MQTT, gather device states, network topology, and error logs.

## What This Command Does

1. Validates environment setup and Playwright MCP availability
2. Reads Home Assistant credentials from `.env` file
3. Analyzes local repository for device context and automations
4. Authenticates to Home Assistant via Playwright browser automation
5. Gathers device state from Developer Tools
6. Inspects device details in Zigbee2MQTT (LQI, last seen, network path)
7. Analyzes logs for errors and connection issues
8. **Researches Zigbee2MQTT documentation** for relevant configuration and troubleshooting
9. Generates comprehensive debug report with recommendations
10. Closes browser session and cleans up

## Usage

```bash
# Debug specific device by entity ID
/zigbee-debug light.bathroom_ambient

# Debug by friendly name
/zigbee-debug "Toilet Motion Sensor"

# Debug by IEEE address
/zigbee-debug 0x00158d0001a2b3c4

# General network health check
/zigbee-debug

# Check specific issues
/zigbee-debug offline
/zigbee-debug battery
```

## Arguments

The command accepts flexible input:

- **Entity ID**: `binary_sensor.toilet_motion` - extracts keywords to search Zigbee2MQTT
- **Friendly name**: `"Kitchen Motion Sensor"` - case-insensitive partial match
- **IEEE address**: `0x00158d0001a2b3c4` - direct lookup (16 hex chars after `0x`)
- **Keywords**: `offline`, `battery`, `network` - special queries for network-wide checks
- **No argument**: General Zigbee network overview

## Environment Setup

### Required Credentials

Read credentials from the `.env` file in the repository root:

```
HOMEASSISTANT_URL=http://homeassistant.local:8123
HOMEASSISTANT_USER=<username>
HOMEASSISTANT_PASSWORD=<password>
ZIGBEE2MQTT_ADDON_ID=45df7312_zigbee2mqtt  # Optional, has default
```

### Key URLs

- Home Assistant: `$HOMEASSISTANT_URL` (from .env)
- Zigbee2MQTT Ingress: `$HOMEASSISTANT_URL/$ZIGBEE2MQTT_ADDON_ID/ingress`
  - Default addon ID: `45df7312_zigbee2mqtt`
  - If different, set `ZIGBEE2MQTT_ADDON_ID` in `.env`

## Workflow Steps

### Step 0: Tool Availability Check

1. Verify Playwright MCP server is available by checking for `mcp__playwright__*` tools
2. If Playwright MCP is not available:
   - Inform user that browser automation requires Playwright MCP server
   - Suggest checking MCP configuration in `.claude/settings.local.json`
   - Exit gracefully without attempting browser operations

### Step 1: Environment Validation

1. Read `.env` file from repository root
2. Verify required variables exist: `HOMEASSISTANT_URL`, `HOMEASSISTANT_USER`, `HOMEASSISTANT_PASSWORD`
3. Check for optional `ZIGBEE2MQTT_ADDON_ID` (use default `45df7312_zigbee2mqtt` if not set)
4. Parse and validate the URL format
5. Inform user of any missing credentials and exit if critical ones missing

### Step 2: Repository Analysis

Before browser automation, analyze the local repository:

1. Use Grep to search `/packages/areas/` for entity references matching the query
2. Find relevant automations: `grep -r "{entity_id_or_name}" packages/areas/*/automations/`
3. Find template sensors: `grep -r "{query}" packages/*/templates/`
4. Note the area directory containing most references
5. Gather context about how the device is used in the smart home

### Step 3: Browser Authentication

Use Playwright MCP to login to Home Assistant:

1. Navigate to `$HOMEASSISTANT_URL` using `mcp__playwright__browser_navigate`
2. Take a snapshot using `mcp__playwright__browser_snapshot` to analyze the page
3. Check if already authenticated (sidebar visible = skip login)
4. If on login page:
   - Fill username field (typically `input[name="username"]`)
   - Fill password field (typically `input[name="password"]`)
   - Click submit button (typically `button[type="submit"]`)
5. Wait for navigation and verify sidebar appears (successful login)

**Error Handling**:

- If already logged in (sidebar visible), proceed to next step
- If login fails after submit, report credentials issue and stop
- If HA unreachable, check URL and network connectivity
- If MFA/2FA prompt appears, inform user this isn't supported and suggest manual login
- Take screenshot on failure to help diagnose selector issues

### Step 4: Gather Device State (Developer Tools)

Navigate to `/developer-tools/state`:

1. Search for entity_id in states list
2. Extract:
   - Current state value
   - Friendly name
   - Last changed/updated timestamps
   - Key attributes (brightness, battery, temperature, etc.)
3. For device name searches, find all related entities

### Step 5: Zigbee2MQTT Inspection

Navigate to `$HOMEASSISTANT_URL/$ZIGBEE2MQTT_ADDON_ID/ingress`:

1. Go to Devices tab/section
2. Search for device by name or IEEE address
3. Extract:
   - **IEEE Address**: Unique device identifier
   - **Friendly Name**: Display name in Zigbee2MQTT
   - **Link Quality (LQI)**: Signal strength 0-255 (higher = better)
   - **Last Seen**: When device last communicated
   - **Battery**: Percentage if battery-powered
   - **Model/Manufacturer**: Device identification
   - **Power Source**: Battery or Mains
4. Check Network Map if available:
   - Parent router for end devices
   - Network path to coordinator
   - Number of hops

**LQI Interpretation**:

- `< 50`: Critical - device will have issues
- `50-100`: Poor - may be unreliable
- `100-150`: Fair - functional but could improve
- `150-255`: Good to Excellent

### Step 6: Log Analysis

Check Zigbee2MQTT logs section:

1. Filter for device name or IEEE address
2. Look for patterns:
   - Connection timeouts
   - Failed message deliveries
   - Device rejoin events
   - Route changes
3. Note error severity and frequency

Also check Home Assistant logs at `/config/logs`:

1. Search for entity_id
2. Look for unavailable state changes
3. Note automation failures related to device

### Step 7: Documentation Research

Use `WebFetch` to research relevant Zigbee2MQTT documentation at `https://www.zigbee2mqtt.io`:

1. **Based on issues found**, fetch relevant documentation pages:
   - Availability issues: `https://www.zigbee2mqtt.io/guide/configuration/device-availability.html`
   - Device-specific issues: `https://www.zigbee2mqtt.io/devices/{MODEL}.html` (e.g., `TS0001_power.html`)
   - Network problems: `https://www.zigbee2mqtt.io/guide/installation/20_zigbee-network.html`
   - Adapter/coordinator issues: `https://www.zigbee2mqtt.io/guide/adapters/`
   - OTA updates: `https://www.zigbee2mqtt.io/guide/usage/ota_updates.html`

2. **Common documentation lookups**:

   | Issue Type | Documentation URL |
   |------------|-------------------|
   | Device availability | `/guide/configuration/device-availability.html` |
   | Device pairing | `/guide/usage/pairing_devices.html` |
   | Touchlink reset | `/guide/usage/touchlink.html` |
   | MQTT configuration | `/guide/configuration/mqtt.html` |
   | Frontend settings | `/guide/configuration/frontend.html` |
   | Logging/debugging | `/guide/configuration/logging.html` |

3. **Extract from documentation**:
   - Correct YAML configuration syntax
   - Default values and recommended settings
   - Troubleshooting steps specific to the issue
   - Any recent changes or deprecations

4. **For device-specific issues**:
   - Look up the device model on `https://www.zigbee2mqtt.io/supported-devices/`
   - Check for known issues, quirks, or required settings
   - Note any OTA firmware updates available

**Example WebFetch calls**:

```
WebFetch(url="https://www.zigbee2mqtt.io/guide/configuration/device-availability.html",
         prompt="Extract the YAML configuration for enabling availability tracking, including all options and defaults")

WebFetch(url="https://www.zigbee2mqtt.io/devices/TS0001_power.html",
         prompt="Extract any known issues, required settings, or quirks for this device")
```

### Step 8: Generate Report

Compile findings into structured markdown report:

```markdown
## Zigbee Debug Report: {device_name}
*Generated: {timestamp}*

### Repository Context
- Area: {area_name}
- Related automations: {list}
- Template sensors: {list}

### Device State (Home Assistant)
- Entity ID: {entity_id}
- Current State: {state}
- Last Changed: {timestamp}
- Key Attributes: {list}

### Zigbee Network
- IEEE Address: {address}
- Model: {model} ({manufacturer})
- Link Quality: {lqi}/255 - {assessment}
- Last Seen: {timestamp}
- Power Source: {battery_or_mains}
- Network Path: Coordinator -> {routers} -> Device

### Issues Found
{list_of_errors_and_warnings}

### Recommendations
{actionable_suggestions}

### Documentation References
- [Relevant Doc 1](https://www.zigbee2mqtt.io/...)
- [Relevant Doc 2](https://www.zigbee2mqtt.io/...)
```

### Step 9: Cleanup

1. Close browser session using `mcp__playwright__browser_close`
2. Confirm report generation is complete
3. Present the final report to the user

## Error Handling

### Authentication Failures

- Verify `.env` credentials are correct
- Test HA URL manually in browser
- Check for MFA/2FA that may require additional handling

### Device Not Found

- List similar device names (fuzzy match)
- Verify device is Zigbee (not Z-Wave, WiFi, etc.)
- Check if entity exists in HA but device not in Zigbee2MQTT

### Zigbee2MQTT Inaccessible

- Verify addon is installed and running
- Check if ingress path changed (different addon ID)
- Try direct access if ingress fails

### Page Load Timeouts

- Increase wait times for slow systems
- Use explicit waits for key elements
- Retry navigation on timeout

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Low LQI (<50) | Device too far from routers | Add Zigbee router between device and coordinator |
| Device offline | Battery dead or out of range | Replace battery, check signal path |
| Frequent rejoins | Unstable connection | Improve mesh, update firmware |
| Slow updates | Network congestion or long route | Add routers, reduce hop count |
| Commands fail | Device unreachable | Check last seen, re-pair if needed |

## Example Outputs

### Healthy Device

```
## Zigbee Debug Report: Toilet Motion Sensor

### Device State
- Entity: binary_sensor.toilet_motion
- State: off
- Battery: 87%

### Zigbee Network
- LQI: 156/255 (Good)
- Last Seen: 2 minutes ago
- Path: Coordinator -> Kitchen Plug -> Device

### Issues Found
None

### Recommendations
Device functioning normally. Battery replacement in ~6 months.
```

### Device with Issues

```
## Zigbee Debug Report: Terrace Motion Sensor

### Device State
- Entity: binary_sensor.terrace_motion
- State: unavailable
- Battery: 45%

### Zigbee Network
- LQI: 42/255 (Critical)
- Last Seen: 3 hours ago
- Path: Coordinator -> Kitchen -> Living Room -> Device (3 hops)

### Issues Found
- Poor signal quality (LQI: 42)
- Device offline for extended period
- 5 rejoin events in last 24 hours

### Recommendations
1. Add router device near terrace to reduce hops
2. Check battery - cold weather reduces performance
3. Consider repositioning closer to indoor router
```

## Notes

- This command is **read-only** - it gathers information but doesn't modify settings
- Browser session is closed after data collection
- Credentials are never displayed or logged in output
- For configuration changes, use Zigbee2MQTT web interface directly
