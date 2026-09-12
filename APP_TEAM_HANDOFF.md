# PhaseGuard - Frontend/App Team Integration Handoff

## WebSocket Contract for Scambaiter Audio

The backend exposes a live, bi-directional WebSocket connection for call audio analysis and scambaiter intervention.

**Endpoint:** 
`ws://<backend_host>/ws/call/{call_id}?token=<jwt>`

### 1. Audio Ingestion (App -> Backend)
The backend expects incoming audio from the user's microphone/call to be sent as **binary frames** in the following format:
* **Format:** Raw PCM16LE (16-bit PCM, Little Endian)
* **Sample Rate:** 16,000 Hz
* **Channels:** 1 (Mono)
* **Chunk Size:** Send in chunks of ~20ms to 50ms for optimal latency.

### 2. Audio Playback (Backend -> App)
When the Scambaiter persona replies, the backend synthesizes speech and streams it back to the client as **binary frames**. 

**CRITICAL NOTE FOR APP TEAM:**
> The backend currently sends the Scambaiter TTS output natively as **MP3 bytes** (or PCM16LE depending on the TTS backend configuration). 
> 
> **Your Responsibility:** Ensure that your app's audio playback engine (e.g., HTML5 `<audio>` in browser, or native AudioTrack in Android/iOS) can natively parse and decode these binary frames. 
> 
> *For Web:* Do not use `AudioContext.decodeAudioData` for raw MP3 streams as it can fail on some browsers. Instead, wrap the binary ArrayBuffer in a Blob and use the native HTML5 `<audio>` element:
> ```javascript
> const blob = new Blob([arrayBuffer], { type: 'audio/mpeg' });
> const url = URL.createObjectURL(blob);
> const audio = new Audio(url);
> audio.play();
> ```

### 3. Event Payloads (JSON)
All non-audio data is sent as JSON strings. Make sure to check if `typeof event.data === 'string'` before running `JSON.parse()`. Key events include:
* `factcheck_update` (Real-time scam detection verdicts)
* `pdi_update` & `tremor_update` (Voice deepfake/DSP metrics)
* `error` / `connected`
