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
