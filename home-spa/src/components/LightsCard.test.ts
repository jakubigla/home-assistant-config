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
