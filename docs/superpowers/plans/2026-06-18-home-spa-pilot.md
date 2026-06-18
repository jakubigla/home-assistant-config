# Home View SPA Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a bespoke Svelte SPA that replaces the wall-tablet Home view, hosted in Home Assistant under `www/`, talking to HA over WebSocket.

**Architecture:** A static Svelte+Vite SPA in `home-spa/`, built to `www/home-spa/` (served at `/local/home-spa/`). A single HA-coupling module (`lib/ha.ts`) owns the WebSocket connection, auth (long-lived token in localStorage), live entity-state store, and `callService`. Derived state lives in `lib/entities.ts`. Dumb presentational cards take state as props and emit service-call events. Surfaced as a fullscreen sidebar panel via `panel_custom` (iframe wrapper).

**Tech Stack:** Svelte 5, Vite, TypeScript, `home-assistant-js-websocket`. Node 22 / npm (confirmed present). No test framework yet → Vitest + `@testing-library/svelte`.

## Global Constraints

- Target device: Samsung SM-T595, **1920×1200, 16:10 landscape**. Design edge-to-edge, **zero scroll**.
- Weak 2018 GPU (Snapdragon 450, 3 GB): minimal `backdrop-filter`, small DOM, **no live video** — doorbell is a polled still image (~1.5 s).
- Long-lived token in `localStorage`; **never commit a token**. Prompt on first load if absent.
- Aesthetic: ambient-stage (locked direction B v2) — dark `radial-gradient` bg, glass cards, amber glow for lit lights, color = information.
- Built `dist/` is committed to `www/home-spa/` (HA git-pulls it; no build on HA side). Source in `home-spa/`.
- A crashing card must never blank the page — each card degrades to an "unknown" state on missing/bad entity.
- Verify entity ids against the **live** HA instance (MCP / hass-cli / API) before wiring — do not trust the YAML.
- Commit after every task. Branch only (current: `chore/june-features` is fine, or a dedicated feature branch). Never push to `main`.

---

### Task 1: Scaffold the Svelte+Vite project and build pipeline

**Files:**
- Create: `home-spa/package.json`, `home-spa/vite.config.ts`, `home-spa/tsconfig.json`, `home-spa/index.html`, `home-spa/src/main.ts`, `home-spa/src/App.svelte`, `home-spa/svelte.config.js`
- Modify: `.gitignore` (append `home-spa/node_modules`, `home-spa/dist`)
- Modify: `justfile` (add `spa-build` / `spa-dev` recipes)

**Interfaces:**
- Produces: a Vite build that emits to `../www/home-spa/` with **relative** asset paths (`base: ''`), so it works under `/local/home-spa/`.

- [ ] **Step 1: Create the Vite project files**

`home-spa/package.json`:
```json
{
  "name": "home-spa",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "devDependencies": {
    "@sveltejs/vite-plugin-svelte": "^5.0.0",
    "@testing-library/svelte": "^5.2.0",
    "@tsconfig/svelte": "^5.0.4",
    "jsdom": "^25.0.0",
    "svelte": "^5.0.0",
    "svelte-check": "^4.0.0",
    "typescript": "^5.6.0",
    "vite": "^6.0.0",
    "vitest": "^2.1.0"
  },
  "dependencies": {
    "home-assistant-js-websocket": "^9.4.0"
  }
}
```

`home-spa/vite.config.ts`:
```ts
import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

export default defineConfig({
  plugins: [svelte()],
  base: '', // relative asset paths so it loads under /local/home-spa/
  build: {
    outDir: '../www/home-spa',
    emptyOutDir: true,
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
})
```

`home-spa/svelte.config.js`:
```js
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte'
export default { preprocess: vitePreprocess() }
```

`home-spa/tsconfig.json`:
```json
{
  "extends": "@tsconfig/svelte/tsconfig.json",
  "compilerOptions": {
    "target": "ESNext",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "verbatimModuleSyntax": true,
    "isolatedModules": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src/**/*.ts", "src/**/*.svelte"]
}
```

`home-spa/index.html`:
```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />
    <title>Home</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

`home-spa/src/main.ts`:
```ts
import { mount } from 'svelte'
import App from './App.svelte'

const app = mount(App, { target: document.getElementById('app')! })
export default app
```

`home-spa/src/App.svelte`:
```svelte
<main>
  <h1>Home SPA — scaffold OK</h1>
</main>

<style>
  :global(html, body) { margin: 0; height: 100%; background: #0a0d14; color: #fff; }
  main { font-family: system-ui, sans-serif; padding: 24px; }
</style>
```

- [ ] **Step 2: Install dependencies**

Run: `cd home-spa && npm install`
Expected: `node_modules/` created, no errors.

- [ ] **Step 3: Ignore build artifacts and deps**

Append to `.gitignore`:
```
home-spa/node_modules
home-spa/dist
```
(Note: `www/home-spa/` is the build output and IS committed — do not ignore it.)

- [ ] **Step 4: Build and verify output lands in www/home-spa**

Run: `cd home-spa && npm run build`
Expected: `www/home-spa/index.html` and `www/home-spa/assets/*` exist; build prints no errors.
Run: `test -f ../www/home-spa/index.html && echo OK`
Expected: `OK`

- [ ] **Step 5: Add just recipes**

Append to `justfile`:
```
# Build the Home SPA into www/home-spa
spa-build:
    cd home-spa && npm run build

# Run the Home SPA dev server
spa-dev:
    cd home-spa && npm run dev
```

- [ ] **Step 6: Commit**

```bash
git add home-spa/package.json home-spa/package-lock.json home-spa/vite.config.ts home-spa/tsconfig.json home-spa/svelte.config.js home-spa/index.html home-spa/src/main.ts home-spa/src/App.svelte www/home-spa .gitignore justfile
git commit -m "feat(home-spa): scaffold Svelte+Vite project, build into config/www"
```

---

### Task 2: HA connection module (`lib/ha.ts`)

**Files:**
- Create: `home-spa/src/lib/ha.ts`
- Test: `home-spa/src/lib/ha.test.ts`

**Interfaces:**
- Produces:
  - `type HassEntity = { entity_id: string; state: string; attributes: Record<string, any>; last_changed: string }`
  - `entities: Readable<Record<string, HassEntity>>` — Svelte store of all entity states.
  - `connectionState: Readable<'connecting' | 'connected' | 'disconnected'>`
  - `async function connect(): Promise<void>` — reads token from localStorage (key `ha_spa_token`), connects, subscribes to all states. Throws `MissingTokenError` if no token.
  - `function setToken(token: string): void` — writes token to localStorage.
  - `function clearToken(): void`
  - `async function callService(domain: string, service: string, data?: object, target?: object): Promise<void>`
  - `class MissingTokenError extends Error {}`
  - `function cameraProxyUrl(entityId: string): string` — returns the signed-less proxy path `/api/camera_proxy/<entity_id>` (auth handled by same-origin session) plus a cache-busting query the caller appends.

- [ ] **Step 1: Write the failing test**

`home-spa/src/lib/ha.test.ts`:
```ts
import { describe, it, expect, beforeEach } from 'vitest'
import { get } from 'svelte/store'
import { setToken, clearToken, connect, MissingTokenError, connectionState, cameraProxyUrl } from './ha'

describe('ha token handling', () => {
  beforeEach(() => localStorage.clear())

  it('throws MissingTokenError when no token is stored', async () => {
    await expect(connect()).rejects.toBeInstanceOf(MissingTokenError)
  })

  it('persists a token to localStorage', () => {
    setToken('abc123')
    expect(localStorage.getItem('ha_spa_token')).toBe('abc123')
    clearToken()
    expect(localStorage.getItem('ha_spa_token')).toBeNull()
  })

  it('starts in connecting state', () => {
    expect(get(connectionState)).toBe('connecting')
  })

  it('builds a camera proxy url', () => {
    expect(cameraProxyUrl('camera.doorbell_rtsp')).toBe('/api/camera_proxy/camera.doorbell_rtsp')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd home-spa && npx vitest run src/lib/ha.test.ts`
Expected: FAIL — `Cannot find module './ha'`.

- [ ] **Step 3: Write the implementation**

`home-spa/src/lib/ha.ts`:
```ts
import { writable, type Readable } from 'svelte/store'
import {
  createConnection,
  createLongLivedTokenAuth,
  subscribeEntities,
  callService as hassCallService,
  type Connection,
  type HassEntities,
} from 'home-assistant-js-websocket'

const TOKEN_KEY = 'ha_spa_token'

export type HassEntity = {
  entity_id: string
  state: string
  attributes: Record<string, any>
  last_changed: string
}

export class MissingTokenError extends Error {
  constructor() {
    super('No Home Assistant token stored')
    this.name = 'MissingTokenError'
  }
}

const _entities = writable<Record<string, HassEntity>>({})
const _connectionState = writable<'connecting' | 'connected' | 'disconnected'>('connecting')

export const entities: Readable<Record<string, HassEntity>> = _entities
export const connectionState: Readable<'connecting' | 'connected' | 'disconnected'> = _connectionState

let conn: Connection | null = null

// SPA is served from /local/home-spa/, same origin as HA, so derive the base URL.
function hassUrl(): string {
  return window.location.origin
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token.trim())
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export async function connect(): Promise<void> {
  const token = getToken()
  if (!token) throw new MissingTokenError()

  const auth = createLongLivedTokenAuth(hassUrl(), token)
  conn = await createConnection({ auth })

  _connectionState.set('connected')
  conn.addEventListener('disconnected', () => _connectionState.set('disconnected'))
  conn.addEventListener('ready', () => _connectionState.set('connected'))

  subscribeEntities(conn, (ents: HassEntities) => {
    _entities.set(ents as unknown as Record<string, HassEntity>)
  })
}

export async function callService(
  domain: string,
  service: string,
  data: object = {},
  target?: object,
): Promise<void> {
  if (!conn) throw new Error('Not connected')
  await hassCallService(conn, domain, service, data, target as any)
}

export function cameraProxyUrl(entityId: string): string {
  return `/api/camera_proxy/${entityId}`
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd home-spa && npx vitest run src/lib/ha.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add home-spa/src/lib/ha.ts home-spa/src/lib/ha.test.ts
git commit -m "feat(home-spa): HA websocket connection module with token auth"
```

---

### Task 3: Derived-state module (`lib/entities.ts`)

**Files:**
- Create: `home-spa/src/lib/entities.ts`
- Test: `home-spa/src/lib/entities.test.ts`

**Interfaces:**
- Consumes: `HassEntity` from `./ha`.
- Produces (pure functions over a `Record<string, HassEntity>` map):
  - `LIGHT_IDS: { id: string; icon: string }[]` — the 8 Home lights with display icons.
  - `function lightsOnCount(map): number`
  - `function isLightOn(map, id): boolean`
  - `function doorStatus(map): { id: string; label: string; open: boolean }[]` — terrace L/R, balcony, garage.
  - `function readyToArm(map): { ready: boolean; openDoors: number; occupiedZones: number }`
  - `function climate(map, room: 'living_room' | 'bedroom'): { temp: number; humidity: number; humidifierOn: boolean }`
  - `function coverPosition(map, id): number` — 0–100.
  - `function applianceState(map): { washer: boolean; dryer: boolean; gfVac: boolean; firstVac: boolean }`
  - Constant entity-id strings exported as `IDS` object (single source of truth).

- [ ] **Step 1: Write the failing test**

`home-spa/src/lib/entities.test.ts`:
```ts
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd home-spa && npx vitest run src/lib/entities.test.ts`
Expected: FAIL — `Cannot find module './entities'`.

- [ ] **Step 3: Write the implementation**

`home-spa/src/lib/entities.ts`:
```ts
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

const num = (v: string | undefined, d = 0): number => {
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd home-spa && npx vitest run src/lib/entities.test.ts`
Expected: PASS (6 tests).

- [ ] **Step 5: Verify entity ids against live HA**

Using MCP `GetLiveContext` or `hass-cli state list`, confirm each id in `IDS` and `LIGHT_IDS` exists. Fix any mismatches in `entities.ts` and re-run the test.
Expected: all ids resolve; test still PASS.

- [ ] **Step 6: Commit**

```bash
git add home-spa/src/lib/entities.ts home-spa/src/lib/entities.test.ts
git commit -m "feat(home-spa): derived entity-state helpers + verified ids"
```

---

### Task 4: Design tokens + global styles

**Files:**
- Create: `home-spa/src/styles/tokens.css`
- Modify: `home-spa/src/App.svelte` (import tokens, set ambient bg)

**Interfaces:**
- Produces: CSS custom properties (`--bg`, `--card`, `--card-brd`, `--txt`, `--dim`, `--amber`, `--green`, `--red`, `--blue`, `--purple`, `--cyan`, `--radius`) used by all cards.

- [ ] **Step 1: Create the tokens**

`home-spa/src/styles/tokens.css`:
```css
:root {
  --bg: #0a0d14;
  --card: rgba(255, 255, 255, 0.05);
  --card-brd: rgba(255, 255, 255, 0.08);
  --txt: #f3f5f8;
  --dim: #9aa3b3;
  --amber: #ffb547;
  --green: #3ddc8f;
  --red: #ff5d6c;
  --blue: #5aa9ff;
  --purple: #b794ff;
  --cyan: #4fd6e0;
  --radius: 18px;
}
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; overflow: hidden; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color: var(--txt);
  -webkit-font-smoothing: antialiased;
  background: radial-gradient(1000px 560px at 72% 12%, #1a2740, var(--bg) 72%);
}
```

- [ ] **Step 2: Wire tokens into App.svelte**

Replace `home-spa/src/App.svelte` with:
```svelte
<script lang="ts">
  import './styles/tokens.css'
</script>

<main>
  <p style="color: var(--dim)">Ambient stage — tokens loaded</p>
</main>

<style>
  main { height: 100vh; padding: 26px 30px; }
</style>
```

- [ ] **Step 3: Build to verify no errors**

Run: `cd home-spa && npm run build`
Expected: build succeeds, `www/home-spa/` regenerated.

- [ ] **Step 4: Commit**

```bash
git add home-spa/src/styles/tokens.css home-spa/src/App.svelte www/home-spa
git commit -m "feat(home-spa): ambient-stage design tokens + global styles"
```

---

### Task 5: Header component (clock, date, weather, people)

**Files:**
- Create: `home-spa/src/components/Header.svelte`
- Test: `home-spa/src/components/Header.test.ts`

**Interfaces:**
- Consumes: `entities` store, `IDS` from `lib/entities`.
- Props: `{ now: Date }` (passed in so it's testable; App ticks it every 30 s).
- Renders: time `HH:MM`, full date, weather temp/condition/humidity from `IDS.weather`, two person avatars (`person.jakub`, `person.sona`) with a green dot when `state === 'home'`, dimmed when away.

- [ ] **Step 1: Write the failing test**

`home-spa/src/components/Header.test.ts`:
```ts
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/svelte'
import Header from './Header.svelte'

describe('Header', () => {
  it('renders the time as HH:MM', () => {
    const { getByText } = render(Header, { props: { now: new Date('2026-06-18T18:42:00') } })
    expect(getByText('18:42')).toBeTruthy()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd home-spa && npx vitest run src/components/Header.test.ts`
Expected: FAIL — `Cannot find module './Header.svelte'`.

- [ ] **Step 3: Write the implementation**

`home-spa/src/components/Header.svelte`:
```svelte
<script lang="ts">
  import { entities } from '../lib/ha'
  import { IDS } from '../lib/entities'

  let { now }: { now: Date } = $props()

  const pad = (n: number) => String(n).padStart(2, '0')
  let time = $derived(`${pad(now.getHours())}:${pad(now.getMinutes())}`)
  let date = $derived(now.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }))

  let w = $derived($entities[IDS.weather])
  let temp = $derived(w ? Math.round(Number(w.attributes?.temperature ?? 0)) : null)
  let cond = $derived(w ? w.state : 'unknown')
  let humidity = $derived(w ? Math.round(Number(w.attributes?.humidity ?? 0)) : null)
  let wind = $derived(w ? Math.round(Number(w.attributes?.wind_speed ?? 0)) : null)

  let jakub = $derived($entities[IDS.personJakub])
  let sona = $derived($entities[IDS.personSona])
</script>

<header>
  <div class="left">
    <div class="time">{time}</div>
    <div class="date">{date}</div>
  </div>
  <div class="right">
    <div class="wx">
      <div class="wt">{temp ?? '–'}°C</div>
      <div class="wc">{cond} · wind {wind ?? '–'} · {humidity ?? '–'}%</div>
    </div>
    <div class="people">
      <span class="av" class:away={jakub?.state !== 'home'} style="background:#3d7dff">J<i></i></span>
      <span class="av" class:away={sona?.state !== 'home'} style="background:#ff5d8a">S<i></i></span>
    </div>
  </div>
</header>

<style>
  header { display: flex; align-items: flex-start; justify-content: space-between; }
  .time { font-size: 58px; font-weight: 300; line-height: .9; letter-spacing: -.02em; }
  .date { font-size: 14px; color: var(--dim); margin-top: 6px; }
  .right { display: flex; align-items: center; gap: 18px; }
  .wt { font-size: 30px; font-weight: 300; text-align: right; }
  .wc { font-size: 12px; color: var(--dim); text-align: right; text-transform: capitalize; }
  .people { display: flex; gap: 8px; }
  .av { width: 42px; height: 42px; border-radius: 50%; display: grid; place-items: center; font-weight: 800; font-size: 15px; color: #fff; position: relative; }
  .av.away { opacity: .4; }
  .av i { position: absolute; bottom: -1px; right: -1px; width: 12px; height: 12px; border-radius: 50%; border: 2px solid var(--bg); background: var(--green); }
  .av.away i { background: var(--dim); }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd home-spa && npx vitest run src/components/Header.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add home-spa/src/components/Header.svelte home-spa/src/components/Header.test.ts
git commit -m "feat(home-spa): Header — clock, weather, presence"
```

---

### Task 6: StatusPills component

**Files:**
- Create: `home-spa/src/components/StatusPills.svelte`
- Test: `home-spa/src/components/StatusPills.test.ts`

**Interfaces:**
- Consumes: `entities` store; `readyToArm`, `doorStatus`, `IDS` from `lib/entities`.
- Renders pills: ready-to-arm (green) or not-ready (red); one warn pill per open door; a "closed" summary pill; occupancy count; active scene from `IDS.scene`.

- [ ] **Step 1: Write the failing test**

`home-spa/src/components/StatusPills.test.ts`:
```ts
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/svelte'
import StatusPills from './StatusPills.svelte'

describe('StatusPills', () => {
  it('renders a not-ready label when no data', () => {
    const { container } = render(StatusPills)
    expect(container.textContent).toContain('Not Ready')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd home-spa && npx vitest run src/components/StatusPills.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the implementation**

`home-spa/src/components/StatusPills.svelte`:
```svelte
<script lang="ts">
  import { entities } from '../lib/ha'
  import { readyToArm, doorStatus, IDS } from '../lib/entities'

  let map = $derived($entities)
  let arm = $derived(readyToArm(map))
  let doors = $derived(doorStatus(map))
  let openDoors = $derived(doors.filter(d => d.open))
  let closedDoors = $derived(doors.filter(d => !d.open))
  let scene = $derived(map[IDS.scene]?.state ?? '–')
</script>

<div class="row">
  <div class="pill" class:ok={arm.ready} class:warn={!arm.ready}>
    <span class="dot" class:red={!arm.ready}></span>
    {arm.ready ? 'Ready to Arm' : 'Not Ready'} · {arm.occupiedZones} zones
  </div>
  {#each openDoors as d}
    <div class="pill warn"><span class="dot red"></span>{d.label} open</div>
  {/each}
  {#if closedDoors.length}
    <div class="pill"><span class="dot"></span>{closedDoors.map(d => d.label).join(' · ')} closed</div>
  {/if}
  <div class="pill"><span style="color:var(--purple)">🎬</span>Scene: {scene}</div>
</div>

<style>
  .row { display: flex; gap: 9px; flex-wrap: wrap; }
  .pill { background: var(--card); border: 1px solid var(--card-brd); border-radius: 999px; padding: 8px 14px; font-size: 12.5px; display: flex; align-items: center; gap: 7px; font-weight: 500; }
  .pill.ok { border-color: rgba(61,220,143,.3); }
  .pill.warn { border-color: rgba(255,93,108,.4); background: rgba(255,93,108,.07); }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); }
  .dot.red { background: var(--red); box-shadow: 0 0 7px var(--red); }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd home-spa && npx vitest run src/components/StatusPills.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add home-spa/src/components/StatusPills.svelte home-spa/src/components/StatusPills.test.ts
git commit -m "feat(home-spa): StatusPills — alarm, doors, scene"
```

---

### Task 7: LightsCard component

**Files:**
- Create: `home-spa/src/components/Card.svelte` (shared glass wrapper)
- Create: `home-spa/src/components/LightsCard.svelte`
- Test: `home-spa/src/components/LightsCard.test.ts`

**Interfaces:**
- `Card.svelte` props: `{ icon?: string; title?: string; children: Snippet }` — the glass card shell (`<div class="glass">` + header). Reused by all stage cards.
- `LightsCard`: consumes `entities`, `LIGHT_IDS`, `isLightOn`, `lightsOnCount`; calls `callService('light','toggle',{},{entity_id})` on tap and `callService('light','turn_off',{},{entity_id:'all'})` on the all-off tile.

- [ ] **Step 1: Write the failing test**

`home-spa/src/components/LightsCard.test.ts`:
```ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, fireEvent } from '@testing-library/svelte'
import LightsCard from './LightsCard.svelte'
import * as ha from '../lib/ha'

describe('LightsCard', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('toggles a light on tap', async () => {
    const spy = vi.spyOn(ha, 'callService').mockResolvedValue()
    const { getByLabelText } = render(LightsCard)
    await fireEvent.click(getByLabelText('light.kitchen'))
    expect(spy).toHaveBeenCalledWith('light', 'toggle', {}, { entity_id: 'light.kitchen' })
  })

  it('turns all lights off on the all-off tile', async () => {
    const spy = vi.spyOn(ha, 'callService').mockResolvedValue()
    const { getByLabelText } = render(LightsCard)
    await fireEvent.click(getByLabelText('all-off'))
    expect(spy).toHaveBeenCalledWith('light', 'turn_off', {}, { entity_id: 'all' })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd home-spa && npx vitest run src/components/LightsCard.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the shared Card shell**

`home-spa/src/components/Card.svelte`:
```svelte
<script lang="ts">
  import type { Snippet } from 'svelte'
  let { icon, title, children }: { icon?: string; title?: string; children: Snippet } = $props()
</script>

<div class="glass">
  {#if title}
    <div class="gh"><span class="gi">{icon}</span><span class="gt">{title}</span></div>
  {/if}
  {@render children()}
</div>

<style>
  .glass { background: var(--card); border: 1px solid var(--card-brd); border-radius: var(--radius); padding: 15px 16px; display: flex; flex-direction: column; min-height: 0; }
  .gh { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
  .gi { font-size: 18px; }
  .gt { font-size: 12px; letter-spacing: .12em; text-transform: uppercase; color: var(--dim); font-weight: 700; }
</style>
```

- [ ] **Step 4: Write LightsCard**

`home-spa/src/components/LightsCard.svelte`:
```svelte
<script lang="ts">
  import Card from './Card.svelte'
  import { entities, callService } from '../lib/ha'
  import { LIGHT_IDS, isLightOn, lightsOnCount } from '../lib/entities'

  let map = $derived($entities)
  let onCount = $derived(lightsOnCount(map))

  function toggle(id: string) {
    callService('light', 'toggle', {}, { entity_id: id })
  }
  function allOff() {
    callService('light', 'turn_off', {}, { entity_id: 'all' })
  }
</script>

<Card icon="💡" title={`Lights · ${onCount} on`}>
  <div class="grid">
    {#each LIGHT_IDS as l}
      <button class="lc" class:on={isLightOn(map, l.id)} aria-label={l.id} onclick={() => toggle(l.id)}>{l.icon}</button>
    {/each}
    <button class="lc off" aria-label="all-off" onclick={allOff}>⏻</button>
  </div>
</Card>

<style>
  .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 7px; flex: 1; }
  .lc { border: none; border-radius: 11px; display: grid; place-items: center; font-size: 18px; background: rgba(255,255,255,.05); color: var(--txt); cursor: pointer; }
  .lc.on { background: radial-gradient(circle at 50% 30%, rgba(255,181,71,.4), rgba(255,181,71,.04)); color: #ffd9a0; }
  .lc.off { color: var(--red); background: rgba(255,93,108,.08); font-size: 15px; }
</style>
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd home-spa && npx vitest run src/components/LightsCard.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add home-spa/src/components/Card.svelte home-spa/src/components/LightsCard.svelte home-spa/src/components/LightsCard.test.ts
git commit -m "feat(home-spa): shared Card shell + LightsCard with toggle/all-off"
```

---

### Task 8: Remaining stage cards (Climate, Media, Doorbell, Curtains, Appliances, QuickPlay, QuickClean)

**Files:**
- Create: `ClimateCard.svelte`, `MediaCard.svelte`, `DoorbellCard.svelte`, `CurtainsCard.svelte`, `AppliancesCard.svelte`, `QuickPlayCard.svelte`, `QuickCleanCard.svelte` (all in `home-spa/src/components/`)
- Test: `home-spa/src/components/stage-cards.test.ts`

**Interfaces:**
- All consume `entities`/`callService` from `lib/ha` and helpers from `lib/entities`. All wrap content in `Card.svelte`.
- `QuickPlayCard` calls `callService('script','turn_on',{},{entity_id})` for the 3 music scripts.
- `QuickCleanCard` calls `callService('script','turn_on',{},{entity_id})` for the 2 vacuum scripts.
- `MediaCard` transport: `callService('media_player', svc, {}, {entity_id: IDS.mediaTv})` where svc ∈ `media_previous_track | media_play_pause | media_next_track`.
- `CurtainsCard` calls `callService('cover','set_cover_position',{position},{entity_id})`.
- `DoorbellCard` renders `<img>` with `cameraProxyUrl(IDS.doorbell)` + `?t=<tick>` refreshed every 1.5 s.

- [ ] **Step 1: Write the failing test**

`home-spa/src/components/stage-cards.test.ts`:
```ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, fireEvent } from '@testing-library/svelte'
import QuickPlayCard from './QuickPlayCard.svelte'
import QuickCleanCard from './QuickCleanCard.svelte'
import MediaCard from './MediaCard.svelte'
import * as ha from '../lib/ha'

describe('stage cards service calls', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('QuickPlay starts the discover-weekly script', async () => {
    const spy = vi.spyOn(ha, 'callService').mockResolvedValue()
    const { getByLabelText } = render(QuickPlayCard)
    await fireEvent.click(getByLabelText('script.music_play_discover_weekly'))
    expect(spy).toHaveBeenCalledWith('script', 'turn_on', {}, { entity_id: 'script.music_play_discover_weekly' })
  })

  it('QuickClean starts the mudroom vacuum script', async () => {
    const spy = vi.spyOn(ha, 'callService').mockResolvedValue()
    const { getByLabelText } = render(QuickCleanCard)
    await fireEvent.click(getByLabelText('script.vacuum_clean_mudroom'))
    expect(spy).toHaveBeenCalledWith('script', 'turn_on', {}, { entity_id: 'script.vacuum_clean_mudroom' })
  })

  it('Media play-pause hits the TV media player', async () => {
    const spy = vi.spyOn(ha, 'callService').mockResolvedValue()
    const { getByLabelText } = render(MediaCard)
    await fireEvent.click(getByLabelText('play-pause'))
    expect(spy).toHaveBeenCalledWith('media_player', 'media_play_pause', {}, { entity_id: 'media_player.living_room_tv' })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd home-spa && npx vitest run src/components/stage-cards.test.ts`
Expected: FAIL — modules not found.

- [ ] **Step 3: Write ClimateCard**

`home-spa/src/components/ClimateCard.svelte`:
```svelte
<script lang="ts">
  import Card from './Card.svelte'
  import { entities } from '../lib/ha'
  import { climate } from '../lib/entities'
  let map = $derived($entities)
  let lr = $derived(climate(map, 'living_room'))
  let br = $derived(climate(map, 'bedroom'))
</script>

<Card icon="🌡️" title="Climate">
  <div class="r">
    <div><div class="n">Living Room</div><div class="h">{lr.humidity}% · <span class:on={lr.humidifierOn}>Humid {lr.humidifierOn ? 'ON' : 'OFF'}</span></div></div>
    <div class="v">{lr.temp.toFixed(1)}°</div>
  </div>
  <div class="r">
    <div><div class="n">Bedroom</div><div class="h">{br.humidity}% · <span class:on={br.humidifierOn}>Humid {br.humidifierOn ? 'ON' : 'OFF'}</span></div></div>
    <div class="v">{br.temp.toFixed(1)}°</div>
  </div>
</Card>

<style>
  .r { display: flex; align-items: baseline; justify-content: space-between; padding: 4px 0; }
  .r + .r { border-top: 1px solid var(--card-brd); }
  .n { font-size: 13px; font-weight: 600; }
  .h { font-size: 11px; color: var(--dim); }
  .h .on { color: var(--cyan); }
  .v { font-size: 18px; font-weight: 700; }
</style>
```

- [ ] **Step 4: Write MediaCard**

`home-spa/src/components/MediaCard.svelte`:
```svelte
<script lang="ts">
  import Card from './Card.svelte'
  import { entities, callService } from '../lib/ha'
  import { IDS } from '../lib/entities'
  let m = $derived($entities[IDS.mediaTv])
  let title = $derived(m?.attributes?.media_title ?? (m?.state === 'playing' ? 'Playing' : 'Idle'))
  let app = $derived(m?.attributes?.app_name ?? 'Living Room TV')
  function ctl(svc: string) {
    callService('media_player', svc, {}, { entity_id: IDS.mediaTv })
  }
</script>

<Card icon="🎵" title="Living Room TV">
  <div class="media">
    <div class="art"></div>
    <div class="info">
      <div class="mt">{title}</div>
      <div class="ms">{app}</div>
      <div class="ctrl">
        <button aria-label="prev" onclick={() => ctl('media_previous_track')}>⏮</button>
        <button aria-label="play-pause" class="p" onclick={() => ctl('media_play_pause')}>⏯</button>
        <button aria-label="next" onclick={() => ctl('media_next_track')}>⏭</button>
      </div>
    </div>
  </div>
</Card>

<style>
  .media { display: flex; gap: 12px; align-items: center; flex: 1; }
  .art { width: 48px; height: 48px; border-radius: 11px; background: linear-gradient(135deg, var(--purple), var(--blue)); flex-shrink: 0; }
  .mt { font-size: 14px; font-weight: 700; }
  .ms { font-size: 11px; color: var(--dim); }
  .ctrl { display: flex; gap: 14px; margin-top: 7px; }
  .ctrl button { background: none; border: none; color: var(--dim); font-size: 16px; cursor: pointer; }
  .ctrl .p { color: var(--txt); }
</style>
```

- [ ] **Step 5: Write DoorbellCard**

`home-spa/src/components/DoorbellCard.svelte`:
```svelte
<script lang="ts">
  import { cameraProxyUrl } from '../lib/ha'
  import { IDS } from '../lib/entities'
  let tick = $state(0)
  // refresh the still image every 1.5s (cheap on weak GPU vs live stream)
  setInterval(() => (tick += 1), 1500)
  let src = $derived(`${cameraProxyUrl(IDS.doorbell)}?t=${tick}`)
</script>

<div class="db">
  <span class="live">● LIVE</span>
  <img alt="Doorbell" {src} />
</div>

<style>
  .db { position: relative; border-radius: var(--radius); overflow: hidden; background: #10141d; border: 1px solid var(--card-brd); display: grid; place-items: center; }
  .db img { width: 100%; height: 100%; object-fit: cover; }
  .live { position: absolute; top: 10px; left: 12px; font-size: 9px; background: var(--red); color: #fff; padding: 2px 7px; border-radius: 5px; font-weight: 800; z-index: 1; }
</style>
```

- [ ] **Step 6: Write CurtainsCard**

`home-spa/src/components/CurtainsCard.svelte`:
```svelte
<script lang="ts">
  import Card from './Card.svelte'
  import { entities, callService } from '../lib/ha'
  import { IDS, coverPosition } from '../lib/entities'
  let map = $derived($entities)
  const rows = [
    { id: IDS.coverGroundFloor, label: 'Ground Floor' },
    { id: IDS.coverBedroom, label: 'Bedroom' },
  ]
  function setPos(id: string, e: Event) {
    const position = Number((e.target as HTMLInputElement).value)
    callService('cover', 'set_cover_position', { position }, { entity_id: id })
  }
</script>

<Card icon="🪟" title="Curtains">
  <div class="body">
    {#each rows as r}
      {@const pos = coverPosition(map, r.id)}
      <div class="cvr">
        <span class="nm">{r.label}</span>
        <input type="range" min="0" max="100" value={pos} aria-label={r.id} onchange={(e) => setPos(r.id, e)} />
        <span class="pct">{pos}%</span>
      </div>
    {/each}
  </div>
</Card>

<style>
  .body { flex: 1; display: flex; flex-direction: column; justify-content: center; }
  .cvr { display: flex; align-items: center; gap: 9px; padding: 5px 0; }
  .nm { font-size: 13px; width: 88px; }
  input[type=range] { flex: 1; accent-color: var(--blue); }
  .pct { font-size: 11px; color: var(--dim); width: 32px; text-align: right; }
</style>
```

- [ ] **Step 7: Write AppliancesCard**

`home-spa/src/components/AppliancesCard.svelte`:
```svelte
<script lang="ts">
  import Card from './Card.svelte'
  import { entities } from '../lib/ha'
  import { applianceState } from '../lib/entities'
  let a = $derived(applianceState($entities))
  let rows = $derived([
    { icon: '🌀', name: 'Washer', on: a.washer, label: a.washer ? 'running' : 'idle' },
    { icon: '🔥', name: 'Dryer', on: a.dryer, label: a.dryer ? 'running' : 'idle' },
    { icon: '🤖', name: 'GF Vac', on: a.gfVac, label: a.gfVac ? 'cleaning' : 'idle' },
    { icon: '🤖', name: '1F Vac', on: a.firstVac, label: a.firstVac ? 'cleaning' : 'idle' },
  ])
</script>

<Card icon="🏠" title="Appliances">
  <div class="mini">
    {#each rows as r}
      <div class="mrow"><span>{r.icon}</span>{r.name}<span class="mv" class:on={r.on}>{r.label}</span></div>
    {/each}
  </div>
</Card>

<style>
  .mini { display: flex; flex-direction: column; gap: 7px; flex: 1; justify-content: center; }
  .mrow { display: flex; align-items: center; gap: 8px; font-size: 12.5px; }
  .mv { margin-left: auto; color: var(--dim); font-size: 11px; }
  .mv.on { color: var(--blue); }
</style>
```

- [ ] **Step 8: Write QuickPlayCard**

`home-spa/src/components/QuickPlayCard.svelte`:
```svelte
<script lang="ts">
  import Card from './Card.svelte'
  import { callService } from '../lib/ha'
  const items = [
    { id: 'script.music_play_discover_weekly', icon: '★', label: 'Discover Weekly', color: 'var(--green)' },
    { id: 'script.music_play_random_playlist', icon: '🔀', label: 'Random Playlist', color: 'var(--purple)' },
    { id: 'script.music_play_last_played', icon: '↺', label: 'Last Played', color: 'var(--blue)' },
  ]
  function play(id: string) { callService('script', 'turn_on', {}, { entity_id: id }) }
</script>

<Card icon="▶" title="Quick Play">
  <div class="mini">
    {#each items as it}
      <button class="mrow" aria-label={it.id} onclick={() => play(it.id)}><span style="color:{it.color}">{it.icon}</span>{it.label}</button>
    {/each}
  </div>
</Card>

<style>
  .mini { display: flex; flex-direction: column; gap: 7px; flex: 1; justify-content: center; }
  .mrow { display: flex; align-items: center; gap: 8px; font-size: 12.5px; background: rgba(255,255,255,.04); border: none; color: var(--txt); padding: 8px 9px; border-radius: 9px; cursor: pointer; text-align: left; }
</style>
```

- [ ] **Step 9: Write QuickCleanCard**

`home-spa/src/components/QuickCleanCard.svelte`:
```svelte
<script lang="ts">
  import Card from './Card.svelte'
  import { entities, callService } from '../lib/ha'
  import { lightsOnCount } from '../lib/entities'
  const items = [
    { id: 'script.vacuum_clean_mudroom', icon: '🚪', label: 'Mudroom' },
    { id: 'script.vacuum_clean_kitchen', icon: '🍴', label: 'Kitchen' },
  ]
  let onCount = $derived(lightsOnCount($entities))
  function clean(id: string) { callService('script', 'turn_on', {}, { entity_id: id }) }
</script>

<Card icon="🧹" title="Quick Clean">
  <div class="mini">
    {#each items as it}
      <button class="mrow" aria-label={it.id} onclick={() => clean(it.id)}><span>{it.icon}</span>{it.label}</button>
    {/each}
    <div class="mrow today"><span>📊</span>Today<span class="mv">{onCount} lights on</span></div>
  </div>
</Card>

<style>
  .mini { display: flex; flex-direction: column; gap: 7px; flex: 1; justify-content: center; }
  .mrow { display: flex; align-items: center; gap: 8px; font-size: 12.5px; background: rgba(255,255,255,.04); border: none; color: var(--txt); padding: 8px 9px; border-radius: 9px; cursor: pointer; text-align: left; }
  .today { background: none; border-top: 1px solid var(--card-brd); border-radius: 0; padding-top: 9px; }
  .mv { margin-left: auto; color: var(--dim); font-size: 11px; }
</style>
```

- [ ] **Step 10: Run test to verify it passes**

Run: `cd home-spa && npx vitest run src/components/stage-cards.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 11: Commit**

```bash
git add home-spa/src/components/ClimateCard.svelte home-spa/src/components/MediaCard.svelte home-spa/src/components/DoorbellCard.svelte home-spa/src/components/CurtainsCard.svelte home-spa/src/components/AppliancesCard.svelte home-spa/src/components/QuickPlayCard.svelte home-spa/src/components/QuickCleanCard.svelte home-spa/src/components/stage-cards.test.ts
git commit -m "feat(home-spa): climate, media, doorbell, curtains, appliances, quick-play/clean cards"
```

---

### Task 9: Dock component (deep-links to existing HA views)

**Files:**
- Create: `home-spa/src/components/Dock.svelte`
- Test: `home-spa/src/components/Dock.test.ts`

**Interfaces:**
- Renders 5 anchor buttons linking (top-level navigation, breaks out of any iframe via `target="_top"`) to `/wall-tablet/climate`, `/media`, `/outdoor`, `/security`, `/settings`.

- [ ] **Step 1: Write the failing test**

`home-spa/src/components/Dock.test.ts`:
```ts
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/svelte'
import Dock from './Dock.svelte'

describe('Dock', () => {
  it('links to the climate view at top level', () => {
    const { getByText } = render(Dock)
    const link = getByText('Climate').closest('a')!
    expect(link.getAttribute('href')).toBe('/wall-tablet/climate')
    expect(link.getAttribute('target')).toBe('_top')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd home-spa && npx vitest run src/components/Dock.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the implementation**

`home-spa/src/components/Dock.svelte`:
```svelte
<script lang="ts">
  const items = [
    { icon: '🌡️', label: 'Climate', href: '/wall-tablet/climate' },
    { icon: '🎬', label: 'Media', href: '/wall-tablet/media' },
    { icon: '🏡', label: 'Outdoor', href: '/wall-tablet/outdoor' },
    { icon: '🛡️', label: 'Security', href: '/wall-tablet/security' },
    { icon: '⚙️', label: 'Settings', href: '/wall-tablet/settings' },
  ]
</script>

<nav class="dock">
  {#each items as it}
    <a class="dbtn" href={it.href} target="_top"><span class="di">{it.icon}</span>{it.label}</a>
  {/each}
</nav>

<style>
  .dock { display: flex; gap: 10px; justify-content: center; }
  .dbtn { flex: 1; max-width: 150px; height: 48px; border-radius: 14px; background: var(--card); border: 1px solid var(--card-brd); display: flex; align-items: center; justify-content: center; gap: 8px; font-size: 13px; font-weight: 600; color: var(--txt); text-decoration: none; }
  .di { font-size: 18px; }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd home-spa && npx vitest run src/components/Dock.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add home-spa/src/components/Dock.svelte home-spa/src/components/Dock.test.ts
git commit -m "feat(home-spa): Dock with deep-links to existing tablet views"
```

---

### Task 10: Assemble App shell, token prompt, connection overlay, layout

**Files:**
- Modify: `home-spa/src/App.svelte`
- Create: `home-spa/src/components/TokenPrompt.svelte`
- Create: `home-spa/src/components/ConnectionOverlay.svelte`
- Test: `home-spa/src/App.test.ts`

**Interfaces:**
- Consumes every card, `Header`, `StatusPills`, `Dock`, plus `connect`, `connectionState`, `getToken`, `setToken`, `MissingTokenError` from `lib/ha`.
- Layout: flex column — `Header` → `StatusPills` → `.stage` (4×2 grid) → `Dock`, sized to `100vh`, no scroll.
- On mount: if `getToken()` is null, show `TokenPrompt`; else call `connect()`. `ConnectionOverlay` shows when `connectionState !== 'connected'`.
- Each card is wrapped in an error boundary (`<svelte:boundary>`) so one failing card cannot blank the page.

- [ ] **Step 1: Write the failing test**

`home-spa/src/App.test.ts`:
```ts
import { describe, it, expect, beforeEach } from 'vitest'
import { render } from '@testing-library/svelte'
import App from './App.svelte'

describe('App', () => {
  beforeEach(() => localStorage.clear())

  it('shows the token prompt when no token is stored', () => {
    const { getByText } = render(App)
    expect(getByText(/paste.*token/i)).toBeTruthy()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd home-spa && npx vitest run src/App.test.ts`
Expected: FAIL — the current App has no token prompt.

- [ ] **Step 3: Write TokenPrompt**

`home-spa/src/components/TokenPrompt.svelte`:
```svelte
<script lang="ts">
  let { onsubmit }: { onsubmit: (token: string) => void } = $props()
  let value = $state('')
</script>

<div class="overlay">
  <div class="box">
    <h2>Connect to Home Assistant</h2>
    <p>Paste a long-lived access token (Profile → Security → Long-lived access tokens).</p>
    <input bind:value placeholder="Long-lived token" />
    <button disabled={!value.trim()} onclick={() => onsubmit(value.trim())}>Connect</button>
  </div>
</div>

<style>
  .overlay { position: fixed; inset: 0; display: grid; place-items: center; background: var(--bg); z-index: 10; }
  .box { background: var(--card); border: 1px solid var(--card-brd); border-radius: var(--radius); padding: 28px; max-width: 460px; }
  h2 { margin: 0 0 8px; font-size: 20px; }
  p { color: var(--dim); font-size: 13px; }
  input { width: 100%; padding: 10px 12px; border-radius: 10px; border: 1px solid var(--card-brd); background: rgba(0,0,0,.3); color: var(--txt); margin: 12px 0; }
  button { padding: 10px 18px; border-radius: 10px; border: none; background: var(--blue); color: #fff; font-weight: 700; cursor: pointer; }
  button:disabled { opacity: .4; }
</style>
```

- [ ] **Step 4: Write ConnectionOverlay**

`home-spa/src/components/ConnectionOverlay.svelte`:
```svelte
<script lang="ts">
  let { state }: { state: 'connecting' | 'connected' | 'disconnected' } = $props()
</script>

{#if state !== 'connected'}
  <div class="ov">{state === 'connecting' ? 'Connecting…' : 'Reconnecting…'}</div>
{/if}

<style>
  .ov { position: fixed; top: 12px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,.6); padding: 6px 16px; border-radius: 999px; font-size: 12px; color: var(--dim); z-index: 20; }
</style>
```

- [ ] **Step 5: Write App.svelte**

`home-spa/src/App.svelte`:
```svelte
<script lang="ts">
  import './styles/tokens.css'
  import { onMount } from 'svelte'
  import { get } from 'svelte/store'
  import { connect, connectionState, getToken, setToken } from './lib/ha'
  import Header from './components/Header.svelte'
  import StatusPills from './components/StatusPills.svelte'
  import LightsCard from './components/LightsCard.svelte'
  import ClimateCard from './components/ClimateCard.svelte'
  import MediaCard from './components/MediaCard.svelte'
  import DoorbellCard from './components/DoorbellCard.svelte'
  import CurtainsCard from './components/CurtainsCard.svelte'
  import AppliancesCard from './components/AppliancesCard.svelte'
  import QuickPlayCard from './components/QuickPlayCard.svelte'
  import QuickCleanCard from './components/QuickCleanCard.svelte'
  import Dock from './components/Dock.svelte'
  import TokenPrompt from './components/TokenPrompt.svelte'
  import ConnectionOverlay from './components/ConnectionOverlay.svelte'

  let needsToken = $state(getToken() === null)
  let now = $state(new Date())

  onMount(() => {
    const clock = setInterval(() => (now = new Date()), 30_000)
    if (!needsToken) connect().catch(() => (needsToken = true))
    return () => clearInterval(clock)
  })

  function onToken(token: string) {
    setToken(token)
    needsToken = false
    connect().catch(() => (needsToken = true))
  }

  const cards = [LightsCard, ClimateCard, MediaCard, DoorbellCard, CurtainsCard, AppliancesCard, QuickPlayCard, QuickCleanCard]
</script>

{#if needsToken}
  <TokenPrompt onsubmit={onToken} />
{:else}
  <ConnectionOverlay state={$connectionState} />
  <main>
    <Header {now} />
    <StatusPills />
    <div class="stage">
      {#each cards as Card}
        <svelte:boundary>
          <Card />
          {#snippet failed()}<div class="cardfail">unavailable</div>{/snippet}
        </svelte:boundary>
      {/each}
    </div>
    <Dock />
  </main>
{/if}

<style>
  main { height: 100vh; padding: 26px 30px; display: flex; flex-direction: column; gap: 18px; }
  .stage { flex: 1; display: grid; grid-template-columns: repeat(4, 1fr); grid-template-rows: 1fr 1fr; gap: 13px; min-height: 0; }
  .stage > :global(*) { min-height: 0; }
  .cardfail { background: var(--card); border: 1px solid var(--card-brd); border-radius: var(--radius); display: grid; place-items: center; color: var(--dim); font-size: 12px; }
</style>
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd home-spa && npx vitest run src/App.test.ts`
Expected: PASS.

- [ ] **Step 7: Run the full test suite + typecheck**

Run: `cd home-spa && npx vitest run && npx svelte-check --tsconfig ./tsconfig.json`
Expected: all tests PASS, svelte-check reports 0 errors.

- [ ] **Step 8: Build**

Run: `cd home-spa && npm run build`
Expected: `www/home-spa/` regenerated, no errors.

- [ ] **Step 9: Commit**

```bash
git add home-spa/src/App.svelte home-spa/src/components/TokenPrompt.svelte home-spa/src/components/ConnectionOverlay.svelte home-spa/src/App.test.ts www/home-spa
git commit -m "feat(home-spa): assemble app shell, token prompt, connection overlay, stage layout"
```

---

### Task 11: Register the HA sidebar panel + deploy + on-device verification

**Files:**
- Modify: `configuration.yaml`
- Create: `home-spa/README.md` (build/deploy/token docs)

**Interfaces:**
- Consumes: built SPA at `/local/home-spa/index.html`.
- Produces: a sidebar panel "Home" pointing at the SPA via `panel_iframe`.

- [ ] **Step 1: Add the panel to configuration.yaml**

Append to `configuration.yaml` (top level, not under `homeassistant:`):
```yaml
panel_iframe:
  home-spa:
    title: "Home SPA"
    icon: mdi:home-assistant
    url: "/local/home-spa/index.html"
    require_admin: false
```

- [ ] **Step 2: Write the README**

`home-spa/README.md`:
```markdown
# Home SPA

Bespoke Svelte dashboard replacing the wall-tablet Home view. Served by HA from `/local/home-spa/`.

## Build
```
cd home-spa && npm install && npm run build   # outputs to ../www/home-spa
```
or `just spa-build`. Commit the regenerated `www/home-spa/` — HA git-pulls it; there is no build step on the HA side.

## Token
First load on a device prompts for a long-lived access token (HA Profile → Security). Stored in `localStorage` key `ha_spa_token`. Never commit a token.

## Panel
Registered in `configuration.yaml` under `panel_iframe: home-spa`. Opens at the sidebar entry "Home SPA".
```

- [ ] **Step 3: Validate HA config**

Run: `just check`
Expected: config check passes (no YAML/schema errors from the new `panel_iframe`).

- [ ] **Step 4: Lint**

Run: `uv run yamllint configuration.yaml`
Expected: no errors.

- [ ] **Step 5: Commit and push**

```bash
git add configuration.yaml home-spa/README.md
git commit -m "feat(home-spa): register sidebar panel + deploy docs"
git push
```

- [ ] **Step 6: Reload HA + check logs**

Per CLAUDE.md: after push, reload HA core config (the new `panel_iframe` needs a restart, not just core-config reload — a full restart registers the panel). Call `homeassistant.restart` via MCP/API (confirm with user first — restart is disruptive), then check logs for panel/registration errors.
Expected: no errors; "Home SPA" appears in the sidebar.

- [ ] **Step 7: On-device / Playwright verification**

Navigate (Playwright, `dangerouslyDisableSandbox: true`) to `http://homeassistant.local:8123/local/home-spa/index.html`, paste a test token, screenshot to `.playwright-mcp/`. Verify: no horizontal/vertical scroll at 1920×1200, all 8 cards render, lights reflect live state, a light toggle works, doorbell image loads.
Expected: screenshot shows the full ambient-stage layout with live data, zero scroll.

- [ ] **Step 8: Final commit (if verification needed tweaks)**

```bash
git add -A && git commit -m "fix(home-spa): on-device layout adjustments" && git push
```

---

## Self-Review Notes

- **Spec coverage:** Svelte+Vite (T1) ✓; `lib/ha.ts` auth/state/callService/camera (T2) ✓; `lib/entities.ts` derived state + verified ids (T3) ✓; design tokens (T4) ✓; Header/StatusPills (T5–6) ✓; all 10 cards incl. all-off, music×3, vacuum×2, climate×2, covers×2, appliances×4 (T7–8) ✓; Dock deep-links (T9) ✓; token prompt + reconnect overlay + per-card error boundary (T10) ✓; panel registration + committed `dist/` + on-device verify (T11) ✓. Camera = polled still image (T8 DoorbellCard) ✓. Zero-scroll 16:10 layout (T10) ✓.
- **Placeholders:** none — every code step has full content.
- **Type consistency:** `callService(domain, service, data, target)` signature identical across T2/T7/T8/T9; `HassEntity` shape shared; `IDS`/`LIGHT_IDS` defined once in T3 and consumed everywhere.
- **Known follow-ups (out of scope, noted for live refinement):** content tuning on real tablet; OAuth; porting the other 9 views; HLS camera.
