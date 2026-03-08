import { useEffect, useRef } from 'react'

type AudioChunkInfo = { data: string; sampleRate: number }

export function useAudioPlayer(chunks: AudioChunkInfo[]): void {
  const contextRef = useRef<AudioContext | null>(null)
  const queueRef = useRef<{ float: Float32Array; rate: number }[]>([])
  const playingRef = useRef(false)
  const processedRef = useRef(0)

  useEffect(() => {
    if (!contextRef.current) {
      // Default to 24000 — Gemini Live output rate
      contextRef.current = new AudioContext({ sampleRate: 24000 })
    }
  }, [])

  useEffect(() => {
    for (let idx = processedRef.current; idx < chunks.length; idx += 1) {
      const { data, sampleRate } = chunks[idx]
      const bytes = Uint8Array.from(atob(data), (ch) => ch.charCodeAt(0))
      const pcm = new Int16Array(bytes.buffer)
      const float = new Float32Array(pcm.length)
      for (let i = 0; i < pcm.length; i += 1) {
        float[i] = pcm[i] / 32768
      }
      queueRef.current.push({ float, rate: sampleRate })
    }
    processedRef.current = chunks.length

    const playNext = () => {
      if (playingRef.current) return
      const ctx = contextRef.current
      if (!ctx) return
      const next = queueRef.current.shift()
      if (!next) return

      playingRef.current = true
      const buffer = ctx.createBuffer(1, next.float.length, next.rate)
      buffer.getChannelData(0).set(next.float)

      const src = ctx.createBufferSource()
      src.buffer = buffer
      src.connect(ctx.destination)
      src.onended = () => {
        playingRef.current = false
        playNext()
      }
      src.start()
    }

    playNext()
  }, [chunks])
}
