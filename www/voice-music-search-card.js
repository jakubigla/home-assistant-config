class VoiceMusicSearchCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._listening = false;
    this._recognition = null;
  }

  set hass(hass) {
    this._hass = hass;
  }

  setConfig(config) {
    this._config = config;
    this._render();
  }

  get _hasSpeechRecognition() {
    return (
      window.isSecureContext &&
      ("SpeechRecognition" in window || "webkitSpeechRecognition" in window)
    );
  }

  _getPlayerEntity() {
    const base = this._hass.states["sensor.media_player_id_by_occupancy"];
    if (base && base.state && base.state.startsWith("media_player.")) {
      return `media_player.mass_${base.state.split(".")[1]}`;
    }
    return "media_player.mass_living_room_tv";
  }

  _playMedia(query) {
    if (!query || !query.trim()) return;
    const entity = this._getPlayerEntity();
    const configEntryId = this._config.config_entry_id || "";

    this._hass.callService("music_assistant", "play_media", {
      media_id: query.trim(),
      media_type: this._config.media_type || "track",
      enqueue: "replace",
      entity_id: entity,
    });

    this._setStatus(`Playing "${query.trim()}"...`);
    setTimeout(() => this._setStatus(""), 3000);
  }

  _setStatus(text) {
    const el = this.shadowRoot.querySelector(".status");
    if (el) el.textContent = text;
  }

  _startListening() {
    if (this._listening) return;

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    this._recognition = new SpeechRecognition();
    this._recognition.lang = this._config.language || "en-US";
    this._recognition.interimResults = false;
    this._recognition.maxAlternatives = 1;

    this._recognition.onstart = () => {
      this._listening = true;
      this._updateMicButton(true);
      this._setStatus("Listening...");
    };

    this._recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      this._setStatus(`Heard: "${transcript}"`);
      this._playMedia(transcript);
    };

    this._recognition.onerror = (event) => {
      this._listening = false;
      this._updateMicButton(false);
      this._setStatus(`Error: ${event.error}`);
      setTimeout(() => this._setStatus(""), 3000);
    };

    this._recognition.onend = () => {
      this._listening = false;
      this._updateMicButton(false);
    };

    this._recognition.start();
  }

  _updateMicButton(active) {
    const btn = this.shadowRoot.querySelector(".mic-btn");
    if (btn) btn.classList.toggle("active", active);
  }

  _render() {
    const useSpeech = this._hasSpeechRecognition;

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
        }
        .container {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px;
          background: var(--ha-card-background, var(--card-background-color, #1c1c1c));
          border-radius: var(--ha-card-border-radius, 12px);
          border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color, #e0e0e0));
        }
        .mic-btn {
          flex-shrink: 0;
          width: 42px;
          height: 42px;
          border-radius: 50%;
          border: none;
          background: var(--primary-color, #03a9f4);
          color: white;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: background 0.2s;
        }
        .mic-btn:hover {
          opacity: 0.85;
        }
        .mic-btn.active {
          background: var(--error-color, #db4437);
          animation: pulse 1s infinite;
        }
        @keyframes pulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.08); }
        }
        .mic-btn svg {
          width: 20px;
          height: 20px;
          fill: currentColor;
        }
        input {
          flex: 1;
          min-width: 0;
          padding: 8px 12px;
          border-radius: 8px;
          border: 1px solid var(--divider-color, #444);
          background: var(--input-fill-color, var(--secondary-background-color, #2c2c2c));
          color: var(--primary-text-color, #fff);
          font-size: 14px;
          font-family: var(--paper-font-body1_-_font-family, inherit);
          outline: none;
        }
        input::placeholder {
          color: var(--secondary-text-color, #999);
        }
        .search-btn {
          flex-shrink: 0;
          width: 42px;
          height: 42px;
          border-radius: 50%;
          border: none;
          background: var(--primary-color, #03a9f4);
          color: white;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .search-btn:hover {
          opacity: 0.85;
        }
        .search-btn svg {
          width: 20px;
          height: 20px;
          fill: currentColor;
        }
        .status {
          font-size: 12px;
          color: var(--secondary-text-color, #999);
          padding: 0 12px 0;
          min-height: 16px;
        }
      </style>
      <div class="container">
        ${
          useSpeech
            ? `<button class="mic-btn" title="Voice search">
                <svg viewBox="0 0 24 24"><path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V5z"/><path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/></svg>
               </button>`
            : ""
        }
        <input type="text" placeholder="Search music..." />
        <button class="search-btn" title="Search">
          <svg viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
        </button>
      </div>
      <div class="status"></div>
    `;

    const input = this.shadowRoot.querySelector("input");
    const searchBtn = this.shadowRoot.querySelector(".search-btn");

    const submitInput = () => this._playMedia(input.value);

    searchBtn.addEventListener("click", () => {
      if (input.value.trim()) {
        submitInput();
        input.value = "";
      }
    });

    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && input.value.trim()) {
        submitInput();
        input.value = "";
      }
    });

    if (useSpeech) {
      const micBtn = this.shadowRoot.querySelector(".mic-btn");
      micBtn.addEventListener("click", () => this._startListening());
    }
  }

  getCardSize() {
    return 1;
  }

  static getStubConfig() {
    return {};
  }
}

customElements.define("voice-music-search-card", VoiceMusicSearchCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "voice-music-search-card",
  name: "Voice Music Search",
  description: "Search and play music via Music Assistant using voice or text",
});
