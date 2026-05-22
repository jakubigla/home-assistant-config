---
summary: Avoid mutually-exclusive visibility pairs on mushroom-template-cards; a crashing card kills its section.
before_action:
  - About to add conditional visibility to a mushroom card
  - About to add a mass-player-card or other crash-prone card
on_symptom:
  - "section renders blank or disappears"
  - "TypeError: Cannot set properties of undefined (setting 'hass')"
---

# Mushroom visibility + crashing cards

## Gotchas

- **Avoid mutually-exclusive visibility pairs on mushroom-template-cards.** Prefer one always-visible card that switches content.
- **A crashing card takes down the entire section's rendering.** `mass-player-card` crashes (`TypeError: Cannot set properties of undefined (setting 'hass')`) when entities don't exist or the "Music Assistant Queue Actions" HACS dep is missing. JS file is `mass-player-card.js`.
