"""Quick WebSocket test for the Quorum backend."""
import asyncio
import json
import websockets


async def test():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as ws:
        print("Connected to WS")

        # Send session.create
        msg = {
            "type": "session.create",
            "config": {
                "agenda": "Should we invest in quantum computing startups this quarter?",
                "selectedAgentIds": ["pa1", "pa2", "pa5"],
            },
        }
        await ws.send(json.dumps(msg))
        print("Sent session.create")

        # Wait for session.ready
        response = await asyncio.wait_for(ws.recv(), timeout=10)
        data = json.loads(response)
        print(f"Received: type={data.get('type')}")
        if data.get("type") == "session.ready":
            agents = data.get("agents", [])
            print(f"  Agents: {[a['name'] for a in agents]}")

        # Now send a text message to get the board talking
        await asyncio.sleep(1)
        text_msg = {
            "type": "text.send",
            "text": "Let's begin the discussion. Each board member, please share your initial thoughts on investing in quantum computing startups.",
        }
        await ws.send(json.dumps(text_msg))
        print("Sent text.send")

        # Collect responses for 30 seconds
        try:
            for _ in range(50):
                response = await asyncio.wait_for(ws.recv(), timeout=30)
                data = json.loads(response)
                msg_type = data.get("type", "?")

                if msg_type == "transcript.add":
                    entry = data.get("entry", {})
                    print(f"  [{entry.get('agentName')}]: {entry.get('text', '')[:120]}")
                elif msg_type == "audio.chunk":
                    print(f"  [audio] {len(data.get('data', ''))} chars b64")
                elif msg_type == "agent.state":
                    print(f"  [state] {data.get('agentId')} -> {data.get('speakingState')}")
                elif msg_type == "session.error":
                    print(f"  [ERROR] {data.get('message')}")
                    break
                else:
                    print(f"  [{msg_type}] {str(data)[:120]}")
        except asyncio.TimeoutError:
            print("Timeout waiting for more messages")

        await ws.close()
        print("Done")


if __name__ == "__main__":
    asyncio.run(test())
