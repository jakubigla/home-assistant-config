# Bedroom Package

This package contains all automations, lights, and configurations for the bedroom and ensuite bathroom areas.

## Presence Automation

The bedroom presence automation (`automations/bedroom_presence.yaml`) provides intelligent lighting control based on occupancy, time of day, and context.

### Features

- **Multi-sensor presence detection**: Combines entrance, walking area, and bed-side presence sensors
- **Adaptive brightness**: Automatically adjusts light levels based on time and context
- **System reliability**: Includes startup triggers and restart mode for handling rapid state changes

### Lighting Scenarios

1. **Daytime Presence** (Not sleeping time)
   - Triggers: Entrance or walking area presence detected
   - Conditions: Dark, no TV playing, lights currently off
   - Action: Turn on reflectors at 100% brightness

2. **Sleeping Time** (During designated sleep hours)
   - Triggers: Entrance presence detected
   - Conditions: Dark, sleeping time active, no TV, lights off
   - Action: Turn on bed stripe at 20% with warm white color (RGB: 249, 255, 194)

3. **Late Night** (23:30 - 06:00)
   - Triggers: Bed-side presence sensors
   - Conditions: Dark, late night hours, lights off
   - Action: Turn on bed stripe at 5% with very warm color (RGB: 255, 200, 150)

4. **No Presence**
   - Triggers: No presence in bedroom or ensuite bathroom
   - Action: Turn off all bedroom lights

### Presence Sensors

- `binary_sensor.bedroom_entrance_presence` - Entrance area detection
- `binary_sensor.bedroom_presence` - Main bedroom area
- `binary_sensor.bedroom_walking_area_presence` - Walking area detection
- `binary_sensor.presence_sensor_bedroom_jakub_side` - Jakub's bed-side sensor
- `binary_sensor.presence_sensor_bedroom_sona_side` - Sona's bed-side sensor
- `binary_sensor.ensuite_bathroom_presence` - Ensuite bathroom detection

### Light Groups

- `light.bedroom` - All bedroom lights group
- `light.bedroom_reflectors` - Main ceiling reflectors
- `light.bed_stripe` - LED stripe under/around bed
- `light.ensuite_bathroom` - Ensuite bathroom lights

### Related Automations

- `ensuite_bathroom_presence.yaml` - Controls ensuite bathroom lighting with similar adaptive logic

## Configuration Files

- `config.yaml` - Main package configuration
- `automations/` - All bedroom-related automations
- `lights/` - Light group definitions
