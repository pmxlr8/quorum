"""Test multi-voice architecture: each agent should have its own voice."""
import asyncio
import json
import websockets

WS_URL = "ws://127.0.0.1:8000/ws"

async def main():
    print("Connecting to", WS_URL)
    async with websockets.connect(WS_URL) as ws:
        # Create session with 3 agents
        await ws.send(json.dumps({
            "type": "session.create",
            "config": {
                "agenda": "Discuss the future of AI in education",
                "selectedAgentIds": ["pa5", "pa1", "pa2"],
            },
        }))

        print("Waiting for session.ready...")
        audio_chunks = 0
        transcripts = []
        agent_states = []
        timeout = 60  # seconds

        try:
            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=5)
                    msg = json.loads(raw)
                    t = msg.get("type", "")

                    if t == "session.ready":
                        agents = msg.get("agents", [])
                        print(f"\n=== SESSION READY ===")
                        for a in agents:
                            print(f"  Agent: {a['name']} (id={a['id']}, role={a['role']})")
                        print()

                        # Send a text message to trigger discussion
                        await asyncio.sleep(1)
                        await ws.send(json.dumps({
                            "type": "text.send",
                            "text": "What are the top 3 opportunities for AI in education?",
                        }))
                        print(">> Sent text message")

                    elif t == "agent.state":
                        agent_states.append(msg)
                        state = msg.get("speakingState", "")
                        agent_id = msg.get("agentId", "")
                        print(f"[STATE] {agent_id} -> {state}")

                    elif t == "transcript.add":
                        entry = msg.get("entry", {})
                        name = entry.get("agentName", "?")
                        text = entry.get("text", "")
                        agent_id = entry.get("agentId", "")
                        transcripts.append(entry)
                        if len(text) > 120:
                            text = text[:120] + "..."
                        print(f"[TRANSCRIPT] [{name}] ({agent_id}): {text}")

                    elif t == "audio.chunk":
                        audio_chunks += 1
                        if audio_chunks % 50 == 0:
                            print(f"  ... {audio_chunks} audio chunks received")

                    elif t == "session.error":
                        print(f"[ERROR] {msg.get('message', '')}")
                        break

                    else:
                        if t not in ("audio.chunk",):
                            print(f"[{t}] {json.dumps(msg)[:100]}")

                except asyncio.TimeoutError:
                    timeout -= 5
                    if timeout <= 0:
                        break
                    if transcripts:
                        print(f"  (waiting... {timeout}s left, {len(transcripts)} transcripts so far)")
                    if len(transcripts) >= 4:  # User + 3 agents
                        print("Got responses from multiple agents, done!")
                        break

        except Exception as e:
            print(f"Error: {e}")

        # Summary
        print(f"\n=== SUMMARY ===")
        print(f"Audio chunks: {audio_chunks}")
        print(f"Transcripts: {len(transcripts)}")
        print(f"Agent states: {len(agent_states)}")

        # Check distinct agents in transcripts
        agent_ids = set(t.get("agentId") for t in transcripts if t.get("agentId") != "user")
        agent_names = set(t.get("agentName") for t in transcripts if t.get("agentName") != "You")
        print(f"Distinct agent IDs in transcripts: {agent_ids}")
        print(f"Distinct agent names in transcripts: {agent_names}")

        if len(agent_ids) >= 2:
            print("\n=== MULTI-VOICE SUCCESS ===")
            print("Multiple distinct agents responded with their own sessions!")
        else:
            print("\nOnly 1 or 0 agents responded - check orchestration")

asyncio.run(main())
