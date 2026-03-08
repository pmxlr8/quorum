from backend.services.live_bridge import LiveBridge


def test_handle_audio_fallback_without_configured_client() -> None:
    bridge = LiveBridge()
    bridge.client = None
    events = bridge._stub_audio_response()
    assert events == []


def test_handle_text_fallback_without_configured_client() -> None:
    bridge = LiveBridge()
    bridge.client = None
    import asyncio

    events = asyncio.run(bridge.handle_text('missing-session', 'hello'))
    assert events[0]['type'] == 'transcript_update'
    assert 'hello' in events[0]['payload']['text']
