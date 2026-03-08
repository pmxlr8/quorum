---
name: hackathon-deploy
description: Deploy backend/frontend for demo reliability on Google Cloud with contract validation and rollback-safe steps.
---

# Hackathon Deploy

Use for pre-demo deployment.

## Steps
1. Validate env vars and model IDs.
2. Deploy backend to Cloud Run (`us-central1`).
3. Validate `/health` and websocket connectivity.
4. Set frontend runtime config to deployed backend.
5. Deploy frontend and verify end-to-end scenario.
6. Save deployed URLs and smoke-test transcript + upload + vote.

## Abort Conditions
- Health check fails
- Voice roundtrip fails
- Upload/doc analysis fails
