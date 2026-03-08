import { useRef } from 'react'

export function useVoiceCapture(onChunk: (base64: string) => void): {
  start: () => Promise<void>
  stop: () => void
} {
  const contextRef = useRef<AudioContext | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)
  const workletRef = useRef<AudioWorkletNode | null>(null)
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const toBase64 = (pcm: Int16Array): string => {
    const bytes = new Uint8Array(pcm.buffer)
    let binary = ''
    for (let i = 0; i < bytes.byteLength; i += 1) {
      binary += String.fromCharCode(bytes[i])
    }
    return btoa(binary)
  }

  const start = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    streamRef.current = stream

    const context = new AudioContext({ sampleRate: 16000 })
    contextRef.current = context

    const source = context.createMediaStreamSource(stream)
    sourceRef.current = source

    try {
      await context.audioWorklet.addModule('/src/worklets/pcm-processor.js')
      const worklet = new AudioWorkletNode(context, 'pcm-processor')
      workletRef.current = worklet
      worklet.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
        onChunk(toBase64(new Int16Array(event.data)))
      }
      source.connect(worklet)
      worklet.connect(context.destination)
    } catch {
      // Fallback path for browsers where AudioWorklet fails to load.
      const processor = context.createScriptProcessor(4096, 1, 1)
      processorRef.current = processor
      processor.onaudioprocess = (evt: AudioProcessingEvent) => {
        const channel = evt.inputBuffer.getChannelData(0)
        const pcm = new Int16Array(channel.length)
        for (let i = 0; i < channel.length; i += 1) {
          const s = Math.max(-1, Math.min(1, channel[i]))
          pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff
        }
        onChunk(toBase64(pcm))
      }
      source.connect(processor)
      processor.connect(context.destination)
    }
  }

  const stop = () => {
    workletRef.current?.disconnect()
    processorRef.current?.disconnect()
    sourceRef.current?.disconnect()
    streamRef.current?.getTracks().forEach((track) => track.stop())
    void contextRef.current?.close()
  }

  return { start, stop }
}
