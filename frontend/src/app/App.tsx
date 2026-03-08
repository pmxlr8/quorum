import { useEffect, useMemo, useState } from 'react'

import { useAudioPlayer } from '../hooks/useAudioPlayer'
import { useVoiceCapture } from '../hooks/useVoiceCapture'
import { useWsStore } from '../store/wsStore'

export function App() {
  const { connect, send, events, connected } = useWsStore()
  const [sessionId] = useState('local-session')
  const [isCapturing, setIsCapturing] = useState(false)

  useEffect(() => {
    connect(sessionId)
  }, [connect, sessionId])

  const audioChunks = useMemo(
    () =>
      events
        .filter((event) => event.type === 'audio_chunk')
        .map((event) => (event.type === 'audio_chunk' ? event.payload.data : ''))
        .filter(Boolean),
    [events],
  )

  useAudioPlayer(audioChunks)

  const voice = useVoiceCapture((data) => send({ type: 'audio', data }))

  return (
    <main style={{ background: '#0a0c11', color: '#fff', minHeight: '100vh', padding: '24px' }}>
      <h1>THE WAR ROOM</h1>
      <p>WS: {connected ? 'connected' : 'disconnected'}</p>
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
        <button
          onClick={async () => {
            if (isCapturing) return
            setIsCapturing(true)
            await voice.start()
          }}
          disabled={isCapturing}
        >
          Start Mic
        </button>
        <button
          onClick={() => {
            if (!isCapturing) return
            voice.stop()
            send({ type: 'turn_complete' })
            setIsCapturing(false)
          }}
          disabled={!isCapturing}
        >
          Stop Mic
        </button>
        <button onClick={() => send({ type: 'text', text: 'What is the technical risk?' })}>Send Text Prompt</button>
      </div>

      <section>
        <h2>Events</h2>
        <ul>
          {events.slice(-20).map((event, idx) => (
            <li key={`${event.type}-${idx}`}>
              <code>{event.type}</code>
            </li>
          ))}
        </ul>
      </section>
    </main>
  )
}
