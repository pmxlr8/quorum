from fastapi.testclient import TestClient

from backend.api.main import app


def test_websocket_text_flow() -> None:
    client = TestClient(app)
    with client.websocket_connect('/ws/test-session') as ws:
        first = ws.receive_json()
        assert first['type'] == 'meeting_status'

        ws.send_json({'type': 'text', 'text': 'hello board'})
        seen_speaking = False
        seen_response = False  # Accept transcript_update OR audio_chunk as valid response

        for _ in range(10):
            event = ws.receive_json()
            if event['type'] == 'agent_speaking':
                seen_speaking = True
            if event['type'] in ('transcript_update', 'audio_chunk'):
                seen_response = True
            if seen_speaking and seen_response:
                break

        assert seen_speaking
        assert seen_response
