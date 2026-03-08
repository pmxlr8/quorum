# Team Members
Anzhelika Siui,
Bhavesh Gupta,
Pranjal Mishra,
Aru Koshkarova


https://www.youtube.com/watch?v=MSZcMDbuw8k


# Virtual War Room

Monorepo:
- `backend/` FastAPI realtime server
- `frontend/` React + TypeScript realtime client
- `infra/` Cloud Run deployment scripts and cloud build configs

## Local Run




Backend:
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.api.main:app --reload --port 8000
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

## Voice Roundtrip Check
```bash
cd backend
python scripts/test_voice_roundtrip.py --url ws://localhost:8000/ws/local-test
```

## Cloud
See `infra/CLOUD_SETUP.md`.

## Live Model Setup (Vertex AI)

Use this when you want real Gemini Live responses (not demo fallback).

1) Authenticate locally:
```bash
gcloud auth application-default login
```

2) Create `backend/.env`:
```bash
cp backend/.env.example backend/.env
```

3) Set Vertex vars in `backend/.env`:
```bash
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=<your-gcp-project-id>
GOOGLE_CLOUD_LOCATION=us-central1
LIVE_MODEL_ID=gemini-live-2.5-flash-native-audio
ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

4) Restart backend and verify:
```bash
curl http://127.0.0.1:8000/health
```
Expect:
- `"live_client_ready": true`
- `"auth_mode": "vertex"`
