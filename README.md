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
