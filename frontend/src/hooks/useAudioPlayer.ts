import { useEffect, useRef } from 'react'

export function useAudioPlayer(base64PcmChunks: string[]): void {
  const contextRef = useRef<AudioContext | null>(null)
  const queueRef = useRef<Float32Array[]>([])
  const playingRef = useRef(false)
  const processedChunksRef = useRef(0)

  useEffect(() => {
    if (!contextRef.current) {
      contextRef.current = new AudioContext({ sampleRate: 16000 })
    }
  }, [])

  useEffect(() => {
    for (let idx = processedChunksRef.current; idx < base64PcmChunks.length; idx += 1) {
      const chunk = base64PcmChunks[idx]
      const bytes = Uint8Array.from(atob(chunk), (ch) => ch.charCodeAt(0))
      const pcm = new Int16Array(bytes.buffer)
      const float = new Float32Array(pcm.length)
      for (let i = 0; i < pcm.length; i += 1) {
        float[i] = pcm[i] / 32768
      }
      queueRef.current.push(float)
    }
    processedChunksRef.current = base64PcmChunks.length

    const playNext = () => {
      if (playingRef.current) return
      const ctx = contextRef.current
      if (!ctx) return
      const next = queueRef.current.shift()
      if (!next) return

      playingRef.current = true
      const buffer = ctx.createBuffer(1, next.length, 16000)
      buffer.getChannelData(0).set(next)

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
  }, [base64PcmChunks])
}
