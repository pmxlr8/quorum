from fastapi.testclient import TestClient

from backend.api.main import app


def receive_until(ws, event_type: str, limit: int = 8) -> dict:
    for _ in range(limit):
        event = ws.receive_json()
        if event.get('type') == event_type:
            return event
    raise AssertionError(f'Event type {event_type} not received within {limit} frames')


def test_websocket_unsupported_event_returns_error() -> None:
    client = TestClient(app)
    with client.websocket_connect('/ws/edge-case-session') as ws:
        first = receive_until(ws, 'meeting_status')
        assert first['type'] == 'meeting_status'

        ws.send_json({'type': 'unknown_event'})
        error = receive_until(ws, 'error')
        assert error['type'] == 'error'
        assert 'Unsupported event' in error['payload']['message']


def test_websocket_vote_event_shape() -> None:
    client = TestClient(app)
    with client.websocket_connect('/ws/vote-session') as ws:
        _ = receive_until(ws, 'meeting_status')

        ws.send_json({'type': 'cast_vote', 'vote': 'yes'})
        vote = receive_until(ws, 'vote_result')
        assert vote['type'] == 'vote_result'
        assert vote['payload']['votes']['user']['vote'] == 'yes'
