import { writable, type Readable } from 'svelte/store'
import {
  createConnection,
  createLongLivedTokenAuth,
  subscribeEntities,
  callService as hassCallService,
  type Connection,
  type HassEntities,
  type HassServiceTarget,
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
export const connectionState: Readable<'connecting' | 'connected' | 'disconnected'> =
  _connectionState

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
  target?: HassServiceTarget,
): Promise<void> {
  if (!conn) throw new Error('Not connected')
  await hassCallService(conn, domain, service, data, target)
}

export function cameraProxyUrl(entityId: string): string {
  return `/api/camera_proxy/${entityId}`
}
