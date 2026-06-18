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
