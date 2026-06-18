import { describe, it, expect } from 'vitest'
import type { HassEntity } from './ha'
import { lightsOnCount, readyToArm, climate, coverPosition, doorStatus, applianceState, IDS } from './entities'

function ent(entity_id: string, state: string, attributes: Record<string, any> = {}): HassEntity {
  return { entity_id, state, attributes, last_changed: '2026-06-18T00:00:00Z' }
}

const map: Record<string, HassEntity> = {
  'light.kitchen': ent('light.kitchen', 'on'),
  'light.bedroom': ent('light.bedroom', 'off'),
  'binary_sensor.home_ready_to_arm': ent('binary_sensor.home_ready_to_arm', 'on', { open_doors_count: 0, occupied_zones_count: 0 }),
  'binary_sensor.balcony_door': ent('binary_sensor.balcony_door', 'on'),
  'binary_sensor.garage_door': ent('binary_sensor.garage_door', 'off'),
  'sensor.living_room_hygro_temperature': ent('sensor.living_room_hygro_temperature', '21.4'),
  'sensor.living_room_hygro_humidity': ent('sensor.living_room_hygro_humidity', '58'),
  'input_boolean.living_room_humidification_active': ent('input_boolean.living_room_humidification_active', 'on'),
  'cover.bedroom': ent('cover.bedroom', 'open', { current_position: 40 }),
  'binary_sensor.washer_power': ent('binary_sensor.washer_power', 'off'),
  'vacuum.dreamebot_l10_ultra': ent('vacuum.dreamebot_l10_ultra', 'cleaning'),
}

describe('derived state', () => {
  it('counts lights that are on', () => {
    expect(lightsOnCount(map)).toBe(1)
  })
  it('reads ready-to-arm rollup', () => {
    expect(readyToArm(map)).toEqual({ ready: true, openDoors: 0, occupiedZones: 0 })
  })
  it('reads climate for a room', () => {
    expect(climate(map, 'living_room')).toEqual({ temp: 21.4, humidity: 58, humidifierOn: true })
  })
  it('reads cover position', () => {
    expect(coverPosition(map, IDS.coverBedroom)).toBe(40)
  })
  it('flags an open door', () => {
    const balcony = doorStatus(map).find(d => d.id === IDS.balconyDoor)
    expect(balcony?.open).toBe(true)
  })
  it('reads appliance running states', () => {
    const a = applianceState(map)
    expect(a.washer).toBe(false)
    expect(a.gfVac).toBe(true)
  })
})
