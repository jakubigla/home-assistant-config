# Stadler Form Noah Humidifier - HA Integration

> **What is this?** A step-by-step guide to connect your
> Stadler Form Noah (or Noah Pro) humidifier to
> Home Assistant so you can control it locally,
> without relying on the cloud.

---

## Table of Contents

1. [Before You Start][s1]
2. [Pair with Smart Life App][s2]
3. [Install HACS][s3]
4. [Install Tuya Local][s4]
5. [Add Noah to Home Assistant][s5]
6. [Verify Everything Works][s6]
7. [What Entities You Get][s7]
8. [DPS Data Points Reference][s8]
9. [Example Automations][s9]
10. [Troubleshooting][s10]
11. [Known Issues][s11]
12. [Sources & Links][s12]

---

## 1. Before You Start - What You Need

Make sure you have ALL of these ready before starting:

- [ ] **Stadler Form Noah** (or Noah Pro),
  plugged in and powered on
- [ ] **Your Wi-Fi password** for your
  **2.4 GHz** network (important - see note below)
- [ ] **A smartphone** (iPhone or Android)
  with the **Smart Life** app installed
- [ ] **Home Assistant** running
  (version **2025.1.0 or newer**)
- [ ] **HACS** (Home Assistant Community Store)
  installed in your Home Assistant
- [ ] Your phone and Home Assistant must be on
  the **same local network** as the Noah

### About the 2.4 GHz Wi-Fi Requirement

This is the #1 thing that trips people up.
The Noah can **ONLY** connect to a 2.4 GHz
Wi-Fi network.

- If your router broadcasts a **single combined
  2.4/5 GHz network** (same name for both),
  the Noah **will NOT connect**. You need to
  either:
  - Log into your router and **split the
    networks** so 2.4 GHz and 5 GHz have
    different names (e.g., `MyWifi` and
    `MyWifi-5G`)
  - Or temporarily **disable the 5 GHz band**
    while pairing
- If your router already has **separate network
  names** for 2.4 GHz and 5 GHz, just make sure
  you connect the Noah to the **2.4 GHz one**
- After pairing is done, you can re-enable your
  combined network or 5 GHz band. The Noah will
  stay connected on 2.4 GHz.

### Which App to Use?

You might already be using the **Stadler Form**
app. That app uses Tuya under the hood, but for
the Home Assistant integration, we need the
**Smart Life** app specifically because it works
with the cloud-assisted setup.

**Important:** A device can only be paired to ONE
app at a time. If you're currently using the
Stadler Form app, you'll need to **remove the
device from that app first**, then pair it fresh
with Smart Life. You cannot have it in both apps
simultaneously.

---

## 2. Step 1: Pair Your Noah with the Smart Life App

If your Noah is already paired with Smart Life,
skip to [Step 2][s3].

### Install the App

1. Open the **App Store** (iPhone) or
   **Google Play Store** (Android)
2. Search for **"Smart Life - Smart Living"**
3. Download and install it
4. Open the app and **create an account**
   (or log in if you already have one)

### Remove from Stadler Form App (if applicable)

If your Noah is currently paired with the
Stadler Form app:

1. Open the **Stadler Form** app
2. Go to your Noah device
3. Tap the **settings/gear icon** (top right)
4. Scroll down and tap **"Remove Device"**
5. Confirm the removal
6. Close the Stadler Form app

### Reset the Noah's Wi-Fi (if needed)

If the Noah was previously connected to a
different app or network, you may need to reset
its Wi-Fi module:

1. On the Noah itself, **press and hold the
   Wi-Fi button** for about 5 seconds
2. The Wi-Fi indicator light should start
   **blinking rapidly** - this means it's in
   pairing mode
3. If you're unsure which button, check your
   Noah's physical manual

### Pair with Smart Life

1. Open the **Smart Life** app
2. Make sure your **phone is connected to your
   2.4 GHz Wi-Fi network**
3. Tap the **"+"** button (top right)
   to add a device
4. The app may auto-detect the Noah. If it does,
   tap on it and follow the prompts
5. If it doesn't auto-detect:
   - Tap **"Small Home Appliances"** in the
     category list on the left
   - Tap **"Humidifier"**
   - Make sure the Noah's Wi-Fi light is
     blinking rapidly
   - Tap **"Next"**
   - Enter your **2.4 GHz Wi-Fi password**
   - Tap **"Next"** and wait for pairing
     to complete
6. Once paired, you should see the Noah in your
   Smart Life app dashboard
7. **Test it:** Try turning it on/off from the
   app to confirm the connection works

### Note Your User Code (you'll need this later)

While you have the Smart Life app open:

1. Tap **"Me"** tab (bottom right)
2. Tap **your account name / profile** at the top
3. Look for **"User Code"** or go to
   **Settings > Account and Security > User Code**
4. **Write down or screenshot this code** -
   you'll need it in Step 4

---

## 3. Step 2: Install HACS (if you don't have it)

HACS (Home Assistant Community Store) is a custom
integration manager. If you already have HACS
installed (you'll see it in the sidebar), skip to
[Step 3][s4].

### How to Tell if You Have HACS

1. Open your Home Assistant web interface
2. Look at the **left sidebar**
3. If you see **"HACS"** in the menu, you
   already have it - skip ahead

### Install HACS

1. Go to <https://hacs.xyz/docs/use/download/download>
2. Follow the official instructions for your
   installation type
3. The easiest method is running this command
   in the **Terminal & SSH** add-on:

   ```bash
   wget -O - https://get.hacs.xyz | bash -
   ```

4. **Restart Home Assistant** after installation
   (Settings > System > Restart)
5. After restart, go to
   **Settings > Devices & Services > Add Integration**
6. Search for **"HACS"** and click it
7. Follow the on-screen prompts to link your
   GitHub account
8. Once done, **"HACS"** will appear in your
   sidebar

---

## 4. Step 3: Install the Tuya Local Integration

This is the integration that actually talks to
your Noah locally.

### Why "Tuya Local" and Not the Built-in "Tuya"?

- The **built-in Tuya integration** routes
  everything through Tuya's cloud servers
  (slower, depends on internet)
- **Tuya Local** talks directly to your device
  on your local network (faster, works without
  internet, more features)

### Install via HACS

1. Open Home Assistant
2. Click **"HACS"** in the left sidebar
3. Click **"Integrations"** at the top
4. Click the **"+"** button (bottom right) or
   the **three-dot menu > Custom repositories**
5. Search for **"Tuya Local"**
   - Look for the one by **make-all**
     (it should have the most stars/downloads)
   - **NOT** "LocalTuya" - that's a different
     integration
6. Click on **"Tuya Local"**
7. Click **"Download"** (or "Install")
8. Choose the latest version (should be
   **2026.1.0 or newer** - Noah support was
   added in this version)
9. Click **"Download"** again to confirm
10. **RESTART Home Assistant** - go to
    **Settings > System > Restart**

### Verify Installation

After restart:

1. Go to **Settings > Devices & Services**
2. Click **"+ Add Integration"**
3. Search for **"Tuya Local"**
4. If it appears in the search results, the
   installation was successful
5. **Don't add it yet** - close this dialog,
   we'll do the actual setup in the next step

---

## 5. Step 4: Add the Noah to Home Assistant

We're going to use the **cloud-assisted setup**,
which is by far the easiest method.

### Prerequisites Check

Before starting, make sure:

- [ ] The Noah is **powered on and connected
  to Wi-Fi** (controllable from Smart Life app)
- [ ] You have your **Smart Life User Code**
  from Step 1
- [ ] Home Assistant and the Noah are on the
  **same local network**
- [ ] The Smart Life app is **closed** on your
  phone (or at least not actively connected
  to the Noah)

### Why Close the Smart Life App?

Tuya devices typically support **only one local
connection at a time**. If the Smart Life app on
your phone is connected to the Noah on your local
network, Tuya Local won't be able to connect.
Close the app or switch to mobile data
temporarily.

### Add the Device

1. Go to **Settings > Devices & Services**
2. Click **"+ Add Integration"** (bottom right)
3. Search for **"Tuya Local"** and click it
4. You'll see two options:
   - **"Add device using cloud-assisted setup"**
     <-- CHOOSE THIS ONE
   - "Add device using manual setup"
5. Click **"Add device using cloud-assisted
   setup"**

### Authenticate with Tuya Cloud

1. You'll see a screen asking for your
   **Smart Life / Tuya Smart user code**
2. Enter the **User Code** you noted in Step 1
3. A **QR code** will appear on the screen
4. Open the **Smart Life** app on your phone
5. Go to **"Me"** tab > tap your
   **profile/account** at the top
6. Look for a **QR code scanner** option
   (or look in Settings)
7. **Scan the QR code** displayed in
   Home Assistant
8. On your phone, **approve/confirm** the
   authorization request
9. Back in Home Assistant, the authentication
   should complete

### Select Your Noah

1. After authentication, you'll see a
   **list of all your Tuya devices**
2. Find and select your **Stadler Form Noah**
   - It might show up as "Noah" or with the
     product name
3. Click **"Next"** or **"Submit"**

### Device Detection

1. Tuya Local will now **scan your local
   network** for the Noah
2. It should auto-detect the device's:
   - **IP address** on your local network
   - **Device ID**
   - **Local key** (the secret encryption key
     for local communication)
3. It will also **auto-detect the device type**
   as a Stadler Form Noah humidifier
4. Review the detected information and click
   **"Submit"**

### Choose Entities

1. You may be asked which entities to create
2. **Accept the defaults** - it will create all
   available entities
   (humidifier, fan, sensors, etc.)
3. Click **"Submit"** / **"Finish"**

### Done

You should now see the Noah listed under
**Settings > Devices & Services > Tuya Local**.

---

## 6. Step 5: Verify Everything Works

### Check the Device Page

1. Go to **Settings > Devices & Services**
2. Find **"Tuya Local"** and click on it
3. Click on the **Noah device**
4. You should see all the entities listed
   (humidifier, fan, sensors, etc.)
5. Each entity should show a **current state**
   (not "unavailable")

### Test Basic Controls

Try these from the Home Assistant UI:

1. **Turn on/off:** Toggle the humidifier
   entity - the Noah should respond within
   1-2 seconds
2. **Set humidity:** Change the target humidity -
   it should accept values from 30% to 80%
   in 5% steps
3. **Fan speed:** Try changing the fan speed
   between levels 1-5
4. **Check sensors:** The current humidity,
   water level, and filter life sensors should
   show real values

### If Something Shows "Unavailable"

- Make sure the Noah is powered on and connected
  to Wi-Fi
- Make sure the Smart Life app is closed on your
  phone
- Check that Home Assistant and the Noah are on
  the same network/subnet
- Try restarting Home Assistant

---

## 7. What Entities You Get

After setup, the Noah creates these entities:

**humidifier.noah** (Humidifier)
: Main control - on/off, target humidity
  (30-80%), mode (auto/normal)

**fan.noah** (Fan)
: Fan speed control with 5 levels
  (20%/40%/60%/80%/100%, where 100% = Turbo)

**lock.noah_child_lock** (Lock)
: Toggle the child lock on/off

**sensor.noah_current_humidity** (Sensor)
: Current room humidity reading (%)

**sensor.noah_filter_life** (Sensor)
: Remaining filter lifespan (%)

**sensor.noah_water_level** (Sensor)
: Current water tank level (%)

**binary_sensor.noah_problem** (Binary Sensor)
: ON when the water tank is empty

**binary_sensor.noah_replace_filter** (Binary Sensor)
: ON when the filter needs replacing

**light.noah_display** (Light)
: Display brightness (Normal/Dimmer/Off) -
  **unreliable, see Known Issues**

> **Note:** The exact entity IDs may vary
> slightly depending on your setup. Check your
> actual entities in
> Settings > Devices & Services > Tuya Local >
> Noah.

---

## 8. DPS Data Points Reference

This is a technical reference. You don't need to
understand this for basic use, but it's helpful
for debugging or building advanced automations.

"DPS" stands for "Data Point Set" - it's how
Tuya devices communicate their features. Each
feature has a numeric ID.

| DP ID | Code | Type | Purpose |
|-------|------|------|---------|
| 1 | `switch` | Boolean | Power on/off |
| 13 | `humidity_current` | Integer | Current humidity |
| 17 | `level_current` | Integer | Water tank level |
| 22 | `fault` | Bitfield | Fault alerts |
| 29 | `child_lock` | Boolean | Child lock |
| 33 | `filter_life` | Integer | Filter life left |
| 101 | `dehumidify_set_enum` | Integer | Target humidity |
| 102 | `fan_speed_enum` | Integer | Fan speed level |
| 103 | `auto_mode` | Boolean | Auto mode |
| 104 | `replace_filter` | Boolean | Filter alert |
| 105 | `night_mode` | Enum | Display brightness |
| 106 | `accessories` | String | Accessories info |

**Ranges:**

- `humidity_current`: 0-100
- `level_current`: 0-100
- `dehumidify_set_enum`: 30-80 (5% steps)
- `fan_speed_enum`: 1-5 (5 = Turbo)
- `night_mode`: Normal / Dimmer / Light_off

### Supported Product IDs

| Model | Tuya Product ID |
|-------|----------------|
| Noah | `hupfwl9kw70i6hoc` |
| Noah Pro | `9b04osuhopcmasq0` |

---

## 9. Example Automations

Here are ready-to-use automation examples you
can place in your Home Assistant configuration.

### Turn On When Humidity Drops Below 40%

```yaml
automation:
  - alias: "Noah - Start when air is dry"
    trigger:
      - platform: numeric_state
        entity_id: sensor.noah_current_humidity
        below: 40
    condition:
      - condition: state
        entity_id: humidifier.noah
        state: "off"
    action:
      - action: humidifier.turn_on
        target:
          entity_id: humidifier.noah
      - action: humidifier.set_humidity
        target:
          entity_id: humidifier.noah
        data:
          humidity: 50
```

### Turn Off When Humidity Reaches Target

```yaml
automation:
  - alias: "Noah - Stop when humidity is good"
    trigger:
      - platform: numeric_state
        entity_id: sensor.noah_current_humidity
        above: 55
    condition:
      - condition: state
        entity_id: humidifier.noah
        state: "on"
    action:
      - action: humidifier.turn_off
        target:
          entity_id: humidifier.noah
```

### Set Auto Mode at Night, Manual During Day

```yaml
automation:
  - alias: "Noah - Night mode (auto + low fan)"
    trigger:
      - platform: time
        at: "22:00:00"
    condition:
      - condition: state
        entity_id: humidifier.noah
        state: "on"
    action:
      - action: humidifier.set_mode
        target:
          entity_id: humidifier.noah
        data:
          mode: auto
      - action: fan.set_percentage
        target:
          entity_id: fan.noah
        data:
          percentage: 20

  - alias: "Noah - Day mode (manual + medium)"
    trigger:
      - platform: time
        at: "08:00:00"
    condition:
      - condition: state
        entity_id: humidifier.noah
        state: "on"
    action:
      - action: humidifier.set_mode
        target:
          entity_id: humidifier.noah
        data:
          mode: normal
      - action: fan.set_percentage
        target:
          entity_id: fan.noah
        data:
          percentage: 60
```

### Notify When Water Tank is Empty

```yaml
automation:
  - alias: "Noah - Water tank empty notification"
    trigger:
      - platform: state
        entity_id: binary_sensor.noah_problem
        to: "on"
    action:
      - action: notify.mobile_app_your_phone
        data:
          title: "Noah Humidifier"
          message: >-
            Water tank is empty!
            Please refill.
```

### Notify When Filter Needs Replacing

```yaml
automation:
  - alias: "Noah - Filter replacement reminder"
    trigger:
      - platform: numeric_state
        entity_id: sensor.noah_filter_life
        below: 10
    action:
      - action: notify.mobile_app_your_phone
        data:
          title: "Noah Humidifier"
          message: >-
            Filter life is at
            {{ states('sensor.noah_filter_life') }}%.
            Time to replace it.
```

### Service Call Quick Reference

```yaml
# Turn on
action: humidifier.turn_on
target:
  entity_id: humidifier.noah

# Turn off
action: humidifier.turn_off
target:
  entity_id: humidifier.noah

# Set target humidity (30-80, in steps of 5)
action: humidifier.set_humidity
target:
  entity_id: humidifier.noah
data:
  humidity: 50

# Set mode
action: humidifier.set_mode
target:
  entity_id: humidifier.noah
data:
  mode: auto  # or "normal"

# Set fan speed (20, 40, 60, 80, or 100)
action: fan.set_percentage
target:
  entity_id: fan.noah
data:
  percentage: 60

# Toggle child lock
action: lock.lock  # or lock.unlock
target:
  entity_id: lock.noah_child_lock
```

---

## 10. Troubleshooting

### "Device not found" during cloud-assisted setup

- Make sure the Noah is powered on and connected
  to Wi-Fi
- Make sure Home Assistant and the Noah are on
  the **same network and subnet**
- The Noah's IP must be reachable from HA. Try
  pinging it from the HA terminal
- If your network uses VLANs or AP isolation,
  the devices may not be able to see each other

### Entity shows "Unavailable"

1. **Close the Smart Life app** on all phones
   on your local network. Tuya devices support
   only one local connection
2. **Check if another Tuya integration** is
   trying to connect to the same device
   (built-in Tuya, LocalTuya, etc.).
   Remove duplicates
3. **Restart Home Assistant** after making
   changes
4. Check the HA logs:
   **Settings > System > Logs** and filter
   for "tuya_local"

### Noah doesn't respond to commands

- The device may have gone offline. Check the
  Smart Life app briefly (then close it)
- The **local key may have changed**. This
  happens if you re-pair the device. You'll
  need to re-add it in Tuya Local
- Check that the protocol version is set
  to **3.4**

### QR code won't scan / authentication fails

- Make sure you're using the **Smart Life** or
  **Tuya Smart** app (not the Stadler Form app)
- Try the User Code from:
  Me > tap profile > Account and Security >
  User Code
- The authentication token expires after a few
  hours. If it fails, restart the setup process

### Noah only connects to 5 GHz / won't pair

- The Noah **cannot** connect to 5 GHz or
  combined 2.4/5 GHz networks
- You must have a **separate 2.4 GHz SSID**
- Log into your router settings and split
  the bands

### "Protocol version mismatch" or connection errors

- The Noah uses Tuya protocol **version 3.4**
- During manual setup, make sure this is set
  correctly
- With cloud-assisted setup, this should be
  auto-detected

### Fan speed won't change

- Fan speed can only be changed when the
  humidifier is **on** and **not** in auto mode
- Switch to `normal` mode first, then set the
  fan speed

---

## 11. Known Issues

### Display Brightness (DPS 105) - Unreliable

The Night Mode / Display brightness control
(DPS 105) has a known bug. When you try to
change the display brightness via Home Assistant:

- The command either **fails to execute**, or
- The state **briefly changes then reverts back**
  to the previous state

**Workaround:** Control the display brightness
directly on the physical device. Do not rely on
automating DPS 105 through Home Assistant. This
is a known issue tracked in
[Issue #4106][issue-4106].

### Local Key Changes on Re-Pairing

Every time you remove and re-pair the Noah in
the Smart Life app, the local encryption key
changes. This means:

- Tuya Local will lose connection
- You'll need to **delete and re-add** the
  device in Tuya Local
- **Avoid re-pairing** unless absolutely
  necessary

### Humidity Target Steps

The target humidity can only be set in
**5% increments**
(30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80).
You cannot set arbitrary values like 42%.

---

## 12. Sources & Links

- [tuya-local GitHub repo][tuya-local]
- [Issue #4106 (Noah support)][issue-4106]
- [PR #4270 (Noah merged)][pr-4270]
- [tuya-local DEVICES.md][devices-md]
- [HA Community: Stadler Form Eva][ha-eva]
- [HACS (download/install)][hacs]
- Smart Life App (iOS): App Store
- Smart Life App (Android): Play Store
- [Stadler Form Wi-Fi instructions][sf-wifi]

---

*Guide created February 2026. Based on
tuya-local release 2026.1.0 which added official
Noah/Noah Pro support.*

[s1]: #1-before-you-start---what-you-need
[s2]: #2-step-1-pair-your-noah-with-the-smart-life-app
[s3]: #3-step-2-install-hacs-if-you-dont-have-it
[s4]: #4-step-3-install-the-tuya-local-integration
[s5]: #5-step-4-add-the-noah-to-home-assistant
[s6]: #6-step-5-verify-everything-works
[s7]: #7-what-entities-you-get
[s8]: #8-dps-data-points-reference
[s9]: #9-example-automations
[s10]: #10-troubleshooting
[s11]: #11-known-issues
[s12]: #12-sources--links
[tuya-local]: https://github.com/make-all/tuya-local
[issue-4106]: https://github.com/make-all/tuya-local/issues/4106
[pr-4270]: https://github.com/make-all/tuya-local/pull/4270
[devices-md]: https://github.com/make-all/tuya-local/blob/main/DEVICES.md
[ha-eva]: https://community.home-assistant.io/t/localtuya-stadler-form-eva-humidifier/414349
[hacs]: https://hacs.xyz
[sf-wifi]: https://www.stadlerform.com/en/service/wi-fi/instruction-noah
