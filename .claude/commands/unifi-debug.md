# Claude Command: UniFi Debug

Troubleshoot UniFi network setup by querying the UniFi Controller API. Generates a markdown report with findings and recommendations.

## What This Command Does

Performs comprehensive UniFi controller diagnostics using the UniFi API via curl. Identifies issues with network devices (APs, switches, gateways), client connectivity, signal strength, channel interference, and retry rates. Supports focused diagnostics for specific areas or full system analysis.

## Usage

```bash
# Full diagnostic (all checks)
/unifi-debug

# Focus on specific area
/unifi-debug devices      # Network devices (APs, switches, gateways)
/unifi-debug clients      # Connected clients and signal strength
/unifi-debug interference # Channel congestion and neighboring APs

# With context about the issue
/unifi-debug there's something wrong with the first floor AP
```

## Environment Setup

### Required Credentials

Read credentials from the `.env` file in the repository root:

```
UNIFI_HOST=https://192.168.1.1/
UNIFI_USER=<username>
UNIFI_PASSWORD=<password>
```

### API Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `POST /api/auth/login` | Authenticate and get session cookie |
| `GET /proxy/network/api/s/default/stat/device` | Get all network devices |
| `GET /proxy/network/api/s/default/stat/sta` | Get all connected clients |
| `GET /proxy/network/api/s/default/stat/rogueap` | Get neighboring APs (interference) |

### Self-Signed Certificate

The UniFi controller uses a self-signed certificate. Use `curl -sk` to skip certificate validation.

## Workflow Steps

### Step 1: Environment Validation

1. Parse the focus argument (if provided) to determine scope
2. Map keywords to check categories:
   - `devices` → network devices inspection
   - `clients` → connected clients inspection
   - `interference` → channel congestion analysis
   - No argument or unrecognized → run all checks
3. Read `.env` file from repository root
4. Verify required variables: `UNIFI_HOST`, `UNIFI_USER`, `UNIFI_PASSWORD`
5. Inform user of missing credentials and exit if critical ones missing

### Step 2: API Authentication

Authenticate with the UniFi Controller API:

```bash
# Create JSON payload file (handles special characters in password)
cat > /tmp/unifi_login.json << 'EOF'
{"username":"$UNIFI_USER","password":"$UNIFI_PASSWORD"}
EOF

# Authenticate and save session cookie
curl -sk -X POST "$UNIFI_HOST/api/auth/login" \
  -H "Content-Type: application/json" \
  -d @/tmp/unifi_login.json \
  -c /tmp/unifi_cookies.txt
```

**Important:** Use a heredoc with single quotes ('EOF') to handle special characters (such as exclamation marks) in passwords.

**Error Handling:**

- HTTP 200 with user JSON = success
- HTTP 401/403 = invalid credentials
- Connection refused = controller unreachable

### Step 3: Network Devices Check

**Run if:** focus is `devices` or full diagnostic

Query device statistics:

```bash
curl -sk "$UNIFI_HOST/proxy/network/api/s/default/stat/device" \
  -b /tmp/unifi_cookies.txt
```

Parse the JSON response to extract for each device:

- **Name**: `data[].name`
- **Model**: `data[].model`
- **Type**: `data[].type` (uap, usw, udm)
- **Status**: `data[].state` (0=disconnected, 1=connected, 2=pending, 4=updating, 5=provisioning)
- **IP Address**: `data[].ip`
- **Uptime**: `data[].uptime` (seconds)
- **CPU/Memory**: `data[].system-stats.cpu`, `data[].system-stats.mem`
- **Clients**: `data[].num_sta` (for APs)
- **Satisfaction**: `data[].satisfaction` (0-100%)

For APs, also extract radio info:

- **Radio Table**: `data[].radio_table[]`
  - Channel: `channel`
  - TX Power Mode: `tx_power_mode`
  - Min RSSI: `min_rssi`
  - HT Width: `ht`

- **Radio Stats**: `data[].radio_table_stats[]`
  - Channel Utilization: `cu_total`
  - Interference: `interference`
  - Connected Clients: `num_sta`

Flag issues:

- CRITICAL: Any device with state=0 (disconnected)
- HIGH: Device with state=2 (pending/unadopted) for extended period
- HIGH: Device with state=4 (updating/rebooting)
- MEDIUM: High CPU (>80%) or memory usage (>80%)
- LOW: Uptime less than 24 hours (recent restart)

### Step 4: Connected Clients Check

**Run if:** focus is `clients` or full diagnostic

Query client statistics:

```bash
curl -sk "$UNIFI_HOST/proxy/network/api/s/default/stat/sta" \
  -b /tmp/unifi_cookies.txt
```

Parse the JSON response to extract for each client:

- **Name/Hostname**: `data[].name` or `data[].hostname` or `data[].mac`
- **Is Wired**: `data[].is_wired`
- **AP MAC**: `data[].ap_mac` (for wireless)
- **Signal**: `data[].signal` (actual RSSI in dBm, negative value)
- **RSSI**: `data[].rssi` (SNR value, positive)
- **Noise**: `data[].noise` (noise floor in dBm)
- **Satisfaction**: `data[].satisfaction`
- **Channel**: `data[].channel`
- **Radio**: `data[].radio` (ng=2.4GHz, na=5GHz)
- **TX/RX Rate**: `data[].tx_rate`, `data[].rx_rate` (in bps, divide by 1000 for Mbps)
- **TX Retries**: `data[].tx_retries`
- **TX Packets**: `data[].tx_packets`

Calculate retry percentage: `(tx_retries / tx_packets) * 100`

**RSSI Interpretation** (WiFi signal strength reference):

- `> -50 dBm`: Excellent
- `-50 to -60 dBm`: Good
- `-60 to -70 dBm`: Fair
- `-70 to -80 dBm`: Poor
- `< -80 dBm`: Very Poor

**Retry Rate Interpretation:**

- `< 10%`: Normal
- `10-30%`: Elevated (monitor)
- `30-50%`: High (investigate)
- `> 50%`: Very High (problem - likely interference)

Flag issues:

- HIGH: Clients with very poor signal (< -80 dBm)
- HIGH: Clients with retry rate > 50%
- MEDIUM: Clients with poor signal (-70 to -80 dBm)
- MEDIUM: Clients with retry rate 30-50%
- LOW: Many clients on 2.4GHz that could use 5GHz

### Step 5: Channel Interference Check

**Run if:** focus is `interference` or full diagnostic

Query neighboring APs (rogue AP detection):

```bash
curl -sk "$UNIFI_HOST/proxy/network/api/s/default/stat/rogueap" \
  -b /tmp/unifi_cookies.txt
```

Parse and count APs per channel:

- Filter for 2.4GHz channels (1-14)
- Count APs on each channel
- Identify the least congested non-overlapping channels (1, 6, 11)

Flag issues:

- HIGH: Current channel has 50+ neighboring APs
- MEDIUM: Current channel has 20-50 neighboring APs
- Recommend: Switch to channel with fewest APs (prefer 1, 6, or 11)

### Step 6: Generate Report

Create markdown report `.reports/UNIFI_REPORT.md` with:

1. **Summary table** - Overall health status per category
2. **Issues Found** - Categorized by severity (Critical, High, Medium, Low)
3. **Detailed Findings**:
   - Device table with status, IP, uptime, clients
   - Radio statistics (channel, utilization, interference)
   - SSID statistics (clients, TX retries)
   - High retry rate clients table
   - Channel congestion analysis
4. **Recommendations** - Actionable steps to resolve issues
5. **Documentation References** - Links to relevant UniFi help articles

### Step 7: Cleanup

```bash
rm -f /tmp/unifi_cookies.txt /tmp/unifi_login.json
```

- Remove temporary credential files
- Confirm report saved to `.reports/UNIFI_REPORT.md`
- Present summary to user with key findings

## Python Parsing Examples

### Parse Device Data

```python
import json
import sys

data = json.load(sys.stdin)
devices = data.get('data', [])

state_map = {0: 'Disconnected', 1: 'Connected', 2: 'Pending', 4: 'Updating', 5: 'Provisioning'}

for d in devices:
    name = d.get('name', 'Unknown')
    model = d.get('model', 'Unknown')
    state = state_map.get(d.get('state', 0), 'Unknown')
    ip = d.get('ip', 'N/A')
    uptime = d.get('uptime', 0)
    uptime_days = uptime // 86400
    uptime_hours = (uptime % 86400) // 3600
    cpu = d.get('system-stats', {}).get('cpu', 'N/A')
    mem = d.get('system-stats', {}).get('mem', 'N/A')
    num_sta = d.get('num_sta', 0)
    satisfaction = d.get('satisfaction', 100)

    print(f'{name} ({model}): {state}, {ip}, {uptime_days}d {uptime_hours}h, {num_sta} clients, {satisfaction}% satisfaction')
```

### Parse Client Data with Retry Analysis

```python
import json
import sys

data = json.load(sys.stdin)
clients = data.get('data', [])

wireless = [c for c in clients if not c.get('is_wired', True)]

for c in sorted(wireless, key=lambda x: x.get('signal', 0)):
    name = c.get('name', c.get('hostname', c.get('mac', 'Unknown')))
    signal = c.get('signal', 0)  # Actual RSSI (negative dBm)
    tx_retries = c.get('tx_retries', 0)
    tx_packets = c.get('tx_packets', 1)
    retry_pct = (tx_retries / tx_packets * 100) if tx_packets > 0 else 0
    channel = c.get('channel', 'N/A')
    radio = c.get('radio', 'N/A')

    print(f'{name}: {signal} dBm, Ch {channel} ({radio}), Retry: {retry_pct:.1f}%')
```

### Count Channel Congestion

```python
import json
import sys
from collections import Counter

data = json.load(sys.stdin)
rogue_aps = data.get('data', [])

channel_count = Counter()
for ap in rogue_aps:
    ch = ap.get('channel', 0)
    if 1 <= ch <= 14:  # 2.4GHz only
        channel_count[ch] += 1

print('2.4GHz Channel Congestion:')
for ch in [1, 6, 11]:  # Non-overlapping channels
    print(f'  Channel {ch}: {channel_count.get(ch, 0)} APs')
```

## Common Issues & Solutions

| Issue | Likely Cause | Recommendation |
|-------|--------------|----------------|
| Device disconnected | Network/power issue | Check physical connection, power cycle |
| Device pending | Never adopted or lost adoption | Adopt device in controller UI |
| Poor client signal | Distance/obstacles | Move closer to AP or add additional AP |
| High retry rate | Channel interference | Change to less congested channel |
| Many APs on same channel | Crowded RF environment | Use channel 1, 6, or 11 with fewest neighbors |
| High CPU on gateway | Heavy traffic/logging | Review traffic rules, reduce logging |

## Error Handling

### Authentication Failures

- HTTP 500 with JSON parse error: Special characters in password not escaped properly - use file input with heredoc
- HTTP 401/403: Invalid credentials
- Connection refused: Controller unreachable, check UNIFI_HOST

### API Errors

- Empty `data` array: No devices/clients found
- Missing fields: Firmware may not expose all stats - note as "N/A"

## Notes

- This command is **read-only** - it gathers information but doesn't modify settings
- Credentials are never displayed in the report
- Temporary files are cleaned up after execution
- Report overwrites previous `.reports/UNIFI_REPORT.md`
- API approach is faster and more reliable than browser automation
