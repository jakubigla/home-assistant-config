import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/svelte'
import Header from './Header.svelte'

describe('Header', () => {
  it('renders the time as HH:MM', () => {
    const { getByText } = render(Header, { props: { now: new Date('2026-06-18T18:42:00') } })
    expect(getByText('18:42')).toBeTruthy()
  })
})
