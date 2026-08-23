---
summary: MA 2.9+ Spotify needs separate playback authorization (librespot) on top of connection auth.
before_action:
  - About to reconfigure or re-authenticate the Music Assistant Spotify provider
on_symptom:
  - "Error loading provider(instance) spotify: Configuration is invalid (will be retried later)"
  - "No playable items found"
  - "Spotify playlists in MA library show 0 tracks while built-in playlists have tracks"
---

# MA Spotify playback authorization

## Gotchas

- **MA 2.9+ Spotify has TWO auth steps: account connection AND playback authorization
  (librespot).** With playback auth missing, the provider load-loops
  `Configuration is invalid (will be retried later)` every 2 min, Spotify-sourced playlists browse
  as 0 tracks, and `music_assistant.play_media` fails with `No playable items found` — while the
  provider page still says "Authenticated to Spotify. No further action required."
- **Use "Authorize playback" + Spotify app device picker** (pick "Music Assistant" like a
  speaker). The "Authorize in browser" flow redirects to `http://127.0.0.1:5588/login?code=...` —
  the listener runs on the MA host, so from any other machine it's "refused to connect" and the
  code expires unused.
- **Click Save in the provider settings after authorizing** — banner says "Playback authorized.
  Don't forget to save to complete setup"; without Save it doesn't persist.
- Fix confirmed loaded when log shows `Successfully logged in to Spotify as <user>` +
  `Loaded music provider Spotify`.
