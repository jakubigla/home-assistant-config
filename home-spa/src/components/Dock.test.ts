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
