import type { HassEntity } from './ha'

type Map = Record<string, HassEntity>

export const IDS = {
  personJakub: 'person.jakub',
  personSona: 'person.sona',
  alarm: 'alarm_control_panel.main',
  readyToArm: 'binary_sensor.home_ready_to_arm',
  terraceLeft: 'binary_sensor.terrace_left_door',
  terraceMain: 'binary_sensor.terrace_main_door',
  balconyDoor: 'binary_sensor.balcony_door',
  garageDoor: 'binary_sensor.garage_door',
  weather: 'weather.forecast_home',
  scene: 'input_select.living_room_scene',
  doorbell: 'camera.doorbell_rtsp',
  mediaTv: 'media_player.living_room_tv',
  coverGroundFloor: 'cover.ground_floor',
  coverBedroom: 'cover.bedroom',
  washer: 'binary_sensor.washer_power',
  dryer: 'binary_sensor.tumble_dryer_power',
  gfVac: 'vacuum.dreamebot_l10_ultra',
  firstVac: 'vacuum.x40_master',
} as const

export const LIGHT_IDS: { id: string; icon: string }[] = [
  { id: 'light.toilet', icon: '🚽' },
  { id: 'light.living_room_corner_lamp', icon: '🛋️' },
  { id: 'light.kitchen', icon: '🍳' },
  { id: 'light.bedroom', icon: '🛏️' },
  { id: 'light.bathroom_main', icon: '🛁' },
  { id: 'light.ensuite_bathroom', icon: '🚿' },
  { id: 'light.hall_bulbs', icon: '🧥' },
  { id: 'light.stairway', icon: '🪜' },
]

const num = (v: string | number | undefined, d = 0): number => {
  const n = Number(v)
  return Number.isFinite(n) ? n : d
}

export function isLightOn(map: Map, id: string): boolean {
  return map[id]?.state === 'on'
}

export function lightsOnCount(map: Map): number {
  return LIGHT_IDS.filter(l => isLightOn(map, l.id)).length
}

export function readyToArm(map: Map): { ready: boolean; openDoors: number; occupiedZones: number } {
  const e = map[IDS.readyToArm]
  return {
    ready: e?.state === 'on',
    openDoors: num(e?.attributes?.open_doors_count),
    occupiedZones: num(e?.attributes?.occupied_zones_count),
  }
}

export function doorStatus(map: Map): { id: string; label: string; open: boolean }[] {
  const defs = [
    { id: IDS.terraceLeft, label: 'Terrace L' },
    { id: IDS.terraceMain, label: 'Terrace R' },
    { id: IDS.balconyDoor, label: 'Balcony' },
    { id: IDS.garageDoor, label: 'Garage' },
  ]
  return defs.map(d => ({ ...d, open: map[d.id]?.state === 'on' }))
}

export function climate(
  map: Map,
  room: 'living_room' | 'bedroom',
): { temp: number; humidity: number; humidifierOn: boolean } {
  return {
    temp: num(map[`sensor.${room}_hygro_temperature`]?.state),
    humidity: num(map[`sensor.${room}_hygro_humidity`]?.state),
    humidifierOn: map[`input_boolean.${room}_humidification_active`]?.state === 'on',
  }
}

export function coverPosition(map: Map, id: string): number {
  return num(map[id]?.attributes?.current_position)
}

export function applianceState(map: Map): { washer: boolean; dryer: boolean; gfVac: boolean; firstVac: boolean } {
  return {
    washer: map[IDS.washer]?.state === 'on',
    dryer: map[IDS.dryer]?.state === 'on',
    gfVac: map[IDS.gfVac]?.state === 'cleaning',
    firstVac: map[IDS.firstVac]?.state === 'cleaning',
  }
}
