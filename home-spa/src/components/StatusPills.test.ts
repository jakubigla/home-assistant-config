import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/svelte'
import StatusPills from './StatusPills.svelte'

describe('StatusPills', () => {
  it('renders a not-ready label when no data', () => {
    const { container } = render(StatusPills)
    expect(container.textContent).toContain('Not Ready')
  })
})
