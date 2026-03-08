"""Verbose WS test - logs all event types received."""
import asyncio
import json
import websockets


async def test():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as ws:
        print("Connected to WS")

        msg = {
            "type": "session.create",
            "config": {
                "agenda": "Should we invest in quantum computing startups?",
                "selectedAgentIds": ["pa1", "pa2", "pa5"],
            },
        }
        await ws.send(json.dumps(msg))
        print("Sent session.create")

        # Wait for session.ready
        response = await asyncio.wait_for(ws.recv(), timeout=10)
        data = json.loads(response)
        print(f"Got: {data.get('type')}")

        # Send text
        await asyncio.sleep(1)
        await ws.send(json.dumps({
            "type": "text.send",
            "text": "Begin the discussion. Each member share thoughts.",
        }))
        print("Sent text.send")

        # Collect ALL messages
        audio_count = 0
        try:
            for _ in range(200):
                response = await asyncio.wait_for(ws.recv(), timeout=30)
                data = json.loads(response)
                t = data.get("type", "?")

                if t == "audio.chunk":
                    audio_count += 1
                    if audio_count % 20 == 0:
                        print(f"  [audio] {audio_count} chunks so far")
                elif t == "transcript.add":
                    e = data.get("entry", {})
                    print(f"  [TRANSCRIPT] [{e.get('agentName')}]: {e.get('text', '')[:150]}")
                elif t == "agent.state":
                    print(f"  [STATE] {data.get('agentId')} -> {data.get('speakingState')}")
                elif t == "vote.proposed":
                    print(f"  [VOTE] {data.get('vote', {}).get('motion', '')[:100]}")
                elif t == "session.error":
                    print(f"  [ERROR] {data.get('message')}")
                    break
                else:
                    print(f"  [{t}] keys={list(data.keys())}")

        except asyncio.TimeoutError:
            print(f"Timeout. Total audio chunks: {audio_count}")

        await ws.close()
        print("Done")


if __name__ == "__main__":
    asyncio.run(test())
