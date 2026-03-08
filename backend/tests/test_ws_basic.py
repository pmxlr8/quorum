from fastapi.testclient import TestClient

from backend.api.main import app


def test_websocket_text_flow() -> None:
    client = TestClient(app)
    with client.websocket_connect('/ws/test-session') as ws:
        first = ws.receive_json()
        assert first['type'] == 'meeting_status'

        ws.send_json({'type': 'text', 'text': 'hello board'})
        msg = ws.receive_json()
        assert msg['type'] == 'transcript_update'
        assert 'hello board' in msg['payload']['text']
