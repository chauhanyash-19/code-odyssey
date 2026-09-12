# PhaseGuard — 360° Multi-Modal Anti-Scam OS

> **7 pillars. Pure software. Built for India.**

PhaseGuard is a real-time voice deepfake detection and scam interception system targeting India's ₹11,000+ crore annual cybercrime problem. No hardware required — everything runs on cloud APIs and a Python/FastAPI backend.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Audio Ingestion Layer                         │
│  browser_mic.py (WebSocket)  ←→  exotel_adapter.py (CPaaS)     │
│                   ↓ shared AudioBufferManager                    │
├──────────────┬──────────────┬──────────────────────────────────┤
│  PILLAR 1    │  PILLAR 3    │  PILLAR 2                         │
│  Bispectrum  │  Micro-Tremor│  LLM Fact-Checker                 │
│  (150ms)     │  (1.5s)      │  STT→Claims→Search→Verdict (2-4s)│
│  ↓ PDI       │  ↓ tremor_E  │  ↓ SAFE/CRITICAL/UNCERTAIN        │
│         ↓    │    ↓         │                                   │
│      Ensemble Score (PDI+tremor+formant)                        │
├─────────────────────────────────────────────────────────────────┤
│  PILLAR 4: AI Scambaiter (confused-elderly persona)             │
│  PILLAR 5: Forensic PDF Dossier (1930 portal format)            │
│  PILLAR 6: Authority Escalation Bridge (human-confirmed)        │
│  PILLAR 7: India Localization (Hindi/Hinglish, Bhashini, MSG91) │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys (Groq minimum required for LLM features)
```

### 3. Run the API

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: http://localhost:8000/docs

### 4. Run the DSP sanity test

```bash
cd backend
python scripts/synthetic_test.py
```

Expected output:
```
✓ PASS: Coherent PDI (0.1xxx) < Incoherent PDI (0.8xxx)
✓ PASS: Phase-randomized signal correctly flagged as SYNTHETIC
ALL ASSERTIONS PASSED — DSP pipeline is correctly functioning ✓
```

---

## REST API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/call/init` | None | Create call session, get JWT |
| WS | `/ws/call/{id}?token=` | JWT | Live audio WebSocket |
| POST | `/call/{id}/scambait` | JWT | Activate AI scambaiter |
| GET | `/call/{id}/dossier` | JWT | Download forensic PDF |
| GET | `/call/{id}/status` | JWT | Current call state + scores |
| POST | `/call/{id}/escalate/draft` | JWT | Draft escalation payload |
| POST | `/call/{id}/escalate/confirm` | JWT | Human-confirmed dispatch |
| POST | `/exotel/stream/{id}` | Exotel signature | Real-call audio webhook |
| GET | `/health` | None | Health check |

---

## WebSocket Messages (server → client)

```json
{"type": "connected", "call_id": "...", "ts": "..."}
{"type": "pdi_update", "pdi_score": 0.85, "is_synthetic": true, "ts": "..."}
{"type": "tremor_update", "tremor_energy": 0.12, "has_tremor": false, "ts": "..."}
{"type": "ensemble_update", "label": "SYNTHETIC", "ensemble_score": 0.78, "ts": "..."}
{"type": "factcheck_update", "status": "CRITICAL", "message": "...", "evidence_urls": [...], "ts": "..."}
{"type": "factcheck_update", "status": "VERIFYING", "message": "Analyzing...", "ts": "..."}
```

---

## India Scam Taxonomy

PhaseGuard pre-classifies calls into India-specific categories:

| Category | Description |
|----------|-------------|
| `DIGITAL_ARREST` | Fake CBI/police/customs "warrant" calls |
| `UPI_COLLECT_FRAUD` | UPI PIN demanded to "receive" money |
| `KYC_SIM_BLOCK` | Fake KYC / SIM block threats |
| `LOAN_HARASSMENT` | Fake loan recovery agents |
| `ELECTRICITY_THREAT` | Electricity disconnection threats |
| `COURIER_CUSTOMS` | Illegal parcel / customs seizure scam |
| `FAKE_JOB_TASK` | Telegram-style fake job/task scams |
| `INVESTMENT_FRAUD` | Fake trading / crypto guaranteed returns |
| `TECH_SUPPORT` | Fake Microsoft/Google support |

**Hardcoded rule:** A UPI PIN is NEVER required to receive money. Any call requesting one is auto-flagged `CRITICAL` regardless of LLM output.

---

## Security Features

- **JWT call tokens** — every WS/REST endpoint requires a short-lived token scoped to a specific `call_id`
- **Prompt injection guard** — transcript content is wrapped in delimiter blocks + keyword rule check
- **Anti-evasion ensemble** — PDI + tremor + formant fusion; disagreement → `UNCERTAIN`, never `SAFE`
- **Rate limiting** — per-IP on LLM/search/TTS endpoints via slowapi
- **WSS enforcement** — plaintext WS rejected in non-dev environments
- **Secret manager abstraction** — pluggable backend (env/Doppler/Infisical/GCP/AWS)

---

## Docker

```bash
docker compose -f infra/docker-compose.yml up --build
```

---

## Report a Scam

- **National Cyber Crime Portal:** https://cybercrime.gov.in
- **Helpline:** 1930 (India)
