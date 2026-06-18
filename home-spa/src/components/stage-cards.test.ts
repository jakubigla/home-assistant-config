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
