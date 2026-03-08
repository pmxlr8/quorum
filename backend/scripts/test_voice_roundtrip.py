"""Basic roundtrip checker for websocket audio path.

Run backend first:
  uvicorn backend.api.main:app --port 8000
"""

from __future__ import annotations

import argparse
import base64
import math
import struct
import time

from websocket import create_connection


def make_sine_pcm16(seconds: float = 1.0, hz: float = 440.0, rate: int = 16000) -> bytes:
    samples = int(seconds * rate)
    out = bytearray()
    for i in range(samples):
        v = int(12000 * math.sin(2 * math.pi * hz * i / rate))
        out.extend(struct.pack('<h', v))
    return bytes(out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='ws://localhost:8000/ws/local-test')
    args = parser.parse_args()

    ws = create_connection(args.url)
    try:
        status = ws.recv()
        print('first-event:', status)
        data = base64.b64encode(make_sine_pcm16()).decode('utf-8')
        start = time.time()
        ws.send('{"type":"audio","data":"' + data + '"}')
        msg = ws.recv()
        latency_ms = int((time.time() - start) * 1000)
        print('audio-response:', msg[:180])
        print(f'latency_ms={latency_ms}')
        print('Voice pipeline OK')
    finally:
        ws.close()


if __name__ == '__main__':
    main()
