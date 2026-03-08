"""Quick WS smoke test for the rewritten orchestration."""
import asyncio
import json
import websockets

async def test():
    uri = "ws://127.0.0.1:8000/ws"
    async with websockets.connect(uri) as ws:
        print("WS connected")
        await ws.send(json.dumps({
            "type": "session.create",
            "config": {
                "agenda": "Test the new orchestration",
                "selectedAgentIds": ["pa1", "pa2"]
            }
        }))
        print("Sent session.create")

        for _ in range(15):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(msg)
                mtype = data.get("type", "?")
                print(f"  <- {mtype}", end="")
                if mtype == "session.ready":
                    names = [a["name"] for a in data.get("agents", [])]
                    print(f"  agents={names}")
                    break
                elif mtype == "session.error":
                    print(f"  ERROR: {data.get('message')}")
                    break
                else:
                    print()
            except asyncio.TimeoutError:
                print("  TIMEOUT")
                break

        await ws.close()
        print("Done")

if __name__ == "__main__":
    asyncio.run(test())
