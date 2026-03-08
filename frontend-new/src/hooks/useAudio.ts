/**
 * Audio utilities for PCM16 capture and playback over WebSocket.
 */

// ── Microphone capture → PCM16 base64 ──────────────────────────────────────

export class MicCapture {
  private stream: MediaStream | null = null;
  private context: AudioContext | null = null;
  private processor: ScriptProcessorNode | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  public onChunk: ((b64: string) => void) | null = null;

  async start(): Promise<void> {
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 16000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });

    this.context = new AudioContext({ sampleRate: 16000 });
    this.source = this.context.createMediaStreamSource(this.stream);

    // ScriptProcessor for raw PCM access (deprecated but universally supported)
    this.processor = this.context.createScriptProcessor(4096, 1, 1);
    this.processor.onaudioprocess = (e) => {
      const float32 = e.inputBuffer.getChannelData(0);
      const pcm16 = float32ToPcm16(float32);
      const b64 = uint8ArrayToBase64(new Uint8Array(pcm16.buffer));
      if (this.onChunk) {
        this.onChunk(b64);
      }
    };

    this.source.connect(this.processor);
    this.processor.connect(this.context.destination);
  }

  stop(): void {
    this.processor?.disconnect();
    this.source?.disconnect();
    this.context?.close();
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
    this.context = null;
    this.processor = null;
    this.source = null;
  }
}

// ── Audio playback from PCM16 base64 ───────────────────────────────────────

export class AudioPlayer {
  private context: AudioContext;
  private queue: AudioBuffer[] = [];
  private playing = false;
  private _muted = false;

  constructor() {
    this.context = new AudioContext({ sampleRate: 24000 });
  }

  set muted(value: boolean) {
    this._muted = value;
  }

  enqueue(b64: string): void {
    if (this._muted) return;

    const pcm16 = base64ToUint8Array(b64);
    const float32 = pcm16ToFloat32(new Int16Array(pcm16.buffer));
    const buffer = this.context.createBuffer(1, float32.length, 24000);
    buffer.getChannelData(0).set(float32);
    this.queue.push(buffer);

    if (!this.playing) {
      this.playNext();
    }
  }

  private playNext(): void {
    if (this.queue.length === 0) {
      this.playing = false;
      return;
    }

    this.playing = true;
    const buffer = this.queue.shift()!;
    const source = this.context.createBufferSource();
    source.buffer = buffer;
    source.connect(this.context.destination);
    source.onended = () => this.playNext();
    source.start();
  }

  flush(): void {
    this.queue = [];
    this.playing = false;
  }

  close(): void {
    this.flush();
    this.context.close();
  }
}

// ── Conversion helpers ─────────────────────────────────────────────────────

function float32ToPcm16(float32: Float32Array): Int16Array {
  const pcm16 = new Int16Array(float32.length);
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]));
    pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return pcm16;
}

function pcm16ToFloat32(pcm16: Int16Array): Float32Array {
  const float32 = new Float32Array(pcm16.length);
  for (let i = 0; i < pcm16.length; i++) {
    float32[i] = pcm16[i] / (pcm16[i] < 0 ? 0x8000 : 0x7fff);
  }
  return float32;
}

function uint8ArrayToBase64(bytes: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function base64ToUint8Array(b64: string): Uint8Array {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}
