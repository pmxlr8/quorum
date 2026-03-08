import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useMemo, useState } from 'react'

import { useAudioPlayer } from '../hooks/useAudioPlayer'
import { useVoiceCapture } from '../hooks/useVoiceCapture'
import { useWsStore } from '../store/wsStore'
import type { ServerEvent } from '../types/events'
import './warroom.css'

type AgentId = 'alex_chen' | 'sarah_kim' | 'marcus_webb' | 'charon_orchestrator'

type AgentView = {
  id: AgentId
  name: string
  role: string
  status: 'idle' | 'speaking'
}

type HealthInfo = {
  status: string
  version: string
  live_model_id: string
  live_client_ready: boolean
  auth_mode: string
  project: string | null
  location: string | null
}

const baseAgents: AgentView[] = [
  { id: 'alex_chen', name: 'Alex Chen', role: 'CTO', status: 'idle' },
  { id: 'sarah_kim', name: 'Sarah Kim', role: 'CFO', status: 'idle' },
  { id: 'marcus_webb', name: 'Marcus Webb', role: 'Legal', status: 'idle' },
  { id: 'charon_orchestrator', name: 'Charon', role: 'Orchestrator', status: 'idle' },
]

function extractTranscript(event: ServerEvent): { speaker: string; text: string } | null {
  if (event.type === 'transcript_update') {
    return { speaker: event.payload.speaker, text: event.payload.text }
  }
  if (event.type === 'error') {
    return { speaker: 'system', text: event.payload.message }
  }
  return null
}

function isAgentSpeaking(event: ServerEvent): event is Extract<ServerEvent, { type: 'agent_speaking' }> {
  return event.type === 'agent_speaking'
}

export function App() {
  const { connect, disconnect, send, events, connected } = useWsStore()
  const [sessionId] = useState('local-session')
  const [isCapturing, setIsCapturing] = useState(false)
  const [prompt, setPrompt] = useState('')
  const [localTranscript, setLocalTranscript] = useState<Array<{ id: string; at: number; speaker: string; text: string }>>([])
  const [health, setHealth] = useState<HealthInfo | null>(null)
  const [healthError, setHealthError] = useState<string | null>(null)

  const httpBase = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

  useEffect(() => {
    connect(sessionId)
    return () => disconnect()
  }, [connect, disconnect, sessionId])

  useEffect(() => {
    let alive = true
    const loadHealth = async () => {
      try {
        const response = await fetch(`${httpBase}/health`)
        if (!response.ok) {
          throw new Error(`Health check failed: ${response.status}`)
        }
        const data = (await response.json()) as HealthInfo
        if (alive) {
          setHealth(data)
          setHealthError(null)
        }
      } catch (error) {
        if (alive) {
          const detail = error instanceof Error ? error.message : 'Unknown health error'
          setHealthError(detail)
        }
      }
    }
    void loadHealth()
    const timer = setInterval(() => {
      void loadHealth()
    }, 5000)
    return () => {
      alive = false
      clearInterval(timer)
    }
  }, [httpBase])

  const audioChunks = useMemo(
    () =>
      events
        .filter((entry) => entry.event.type === 'audio_chunk')
        .map((entry) => (entry.event.type === 'audio_chunk' ? entry.event.payload.data : ''))
        .filter(Boolean),
    [events],
  )

  const transcript = useMemo(
    () =>
      events
        .map((entry) => ({ id: entry.id, at: entry.at, data: extractTranscript(entry.event) }))
        .filter((entry): entry is { id: string; at: number; data: { speaker: string; text: string } } => Boolean(entry.data)),
    [events],
  )

  const mergedTranscript = useMemo(
    () =>
      [...transcript.map((entry) => ({ ...entry.data, id: entry.id, at: entry.at })), ...localTranscript]
        .sort((a, b) => a.at - b.at)
        .slice(-40),
    [localTranscript, transcript],
  )

  const agents = useMemo(() => {
    const next = baseAgents.map((a) => ({ ...a }))
    const speaking = [...events].reverse().map((entry) => entry.event).find(isAgentSpeaking)

    if (speaking) {
      const agent = next.find((a) => a.id === speaking.payload.agent)
      if (agent) {
        agent.status = 'speaking'
      }
    }
    return next
  }, [events])

  useAudioPlayer(audioChunks)

  const addLocalEntry = (speaker: string, text: string) => {
    setLocalTranscript((entries) => [
      ...entries,
      { id: `local-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, at: Date.now(), speaker, text },
    ])
  }

  const sendUserText = (text: string) => {
    const trimmed = text.trim()
    if (!trimmed) return
    addLocalEntry('you', trimmed)
    send({ type: 'text', text: trimmed })
  }

  const voice = useVoiceCapture((data) => send({ type: 'audio', data }))

  return (
    <main className="warroom-root">
      <motion.header className="topbar" initial={{ y: -12, opacity: 0 }} animate={{ y: 0, opacity: 1 }}>
        <div className="title-wrap">
          <h1 className="title">THE WAR ROOM</h1>
          <span className="pill">BOARD DECISION SIM</span>
        </div>
        <div className="topbar-right">
          <div className={`pill mode-pill ${health?.live_client_ready ? 'live' : 'demo'}`}>
            {health?.live_client_ready ? 'LIVE MODEL READY' : 'DEMO MODE'}
          </div>
          <div className="pill">
            <span className={`live-dot ${connected ? 'on' : ''}`} />
            {connected ? 'CONNECTED' : 'DISCONNECTED'}
          </div>
        </div>
      </motion.header>

      <motion.section className="status-grid" initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}>
        <article className="status-tile">
          <span className="status-k">Auth</span>
          <span className="status-v">{health?.auth_mode ?? 'unknown'}</span>
        </article>
        <article className="status-tile">
          <span className="status-k">Model</span>
          <span className="status-v">{health?.live_model_id ?? 'unavailable'}</span>
        </article>
        <article className="status-tile">
          <span className="status-k">Project</span>
          <span className="status-v">{health?.project ?? 'not set'}</span>
        </article>
        <article className="status-tile">
          <span className="status-k">Region</span>
          <span className="status-v">{health?.location ?? 'not set'}</span>
        </article>
      </motion.section>

      {healthError ? <div className="warn-banner">Health check error: {healthError}</div> : null}
      {health && !health.live_client_ready ? (
        <div className="warn-banner">
          Live auth is not configured. Text uses local demo fallback; microphone will not produce real model responses.
        </div>
      ) : null}

      <section className="mission">
        <div className="mission-title">Current Mission</div>
        <div className="mission-text">Decide the next product milestone with clear Decision, Risks, and Owner outputs for the executive board.</div>
      </section>

      <section className="layout">
        <motion.aside className="panel" initial={{ opacity: 0, x: -18 }} animate={{ opacity: 1, x: 0 }}>
          <div className="panel-head">BOARD MEMBERS</div>
          <div className="panel-body agent-list">
            {agents.map((agent) => (
              <motion.article
                key={agent.id}
                layout
                className="agent-card"
                animate={{
                  borderColor: agent.status === 'speaking' ? 'rgba(28, 200, 255, 0.7)' : 'rgba(255,255,255,0.12)',
                  boxShadow: agent.status === 'speaking' ? '0 0 0 1px rgba(28,200,255,.35), 0 0 26px rgba(28,200,255,.24)' : 'none',
                }}
              >
                <div className="agent-row">
                  <div>
                    <div className="agent-name">{agent.name}</div>
                    <div className="agent-role">{agent.role}</div>
                  </div>
                  <span className="status-tag">{agent.status.toUpperCase()}</span>
                </div>
              </motion.article>
            ))}
          </div>
        </motion.aside>

        <div className="center-stack">
          <motion.section className="panel control-card" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}>
            <div className="panel-head">VOICE COMMAND DECK</div>
            <div className="panel-body control-grid">
              <motion.button
                className="mic-orb"
                whileTap={{ scale: 0.93 }}
                animate={isCapturing ? { boxShadow: ['0 0 0 0 rgba(46,229,157,.55)', '0 0 0 18px rgba(46,229,157,0)'] } : {}}
                transition={{ repeat: isCapturing ? Number.POSITIVE_INFINITY : 0, duration: 1.2 }}
                onClick={async () => {
                  if (isCapturing) {
                    voice.stop()
                    send({ type: 'turn_complete' })
                    setIsCapturing(false)
                    addLocalEntry('you', '[voice] Turn complete.')
                    return
                  }
                  try {
                    setIsCapturing(true)
                    await voice.start()
                    addLocalEntry('you', '[voice] Listening...')
                  } catch (error) {
                    setIsCapturing(false)
                    const detail = error instanceof Error ? error.message : 'Unknown microphone error'
                    addLocalEntry('system', `Microphone failed to start: ${detail}`)
                  }
                }}
              >
                {isCapturing ? 'STOP MIC' : 'START MIC'}
              </motion.button>

              <div>
                <div className="controls">
                  <button className="btn primary" onClick={() => sendUserText('Evaluate technical scalability risk for this quarter.')}>
                    Ask CTO
                  </button>
                  <button className="btn" onClick={() => sendUserText('Assess budget, margin, and runway implications.')}>
                    Ask CFO
                  </button>
                  <button className="btn" onClick={() => sendUserText('Check legal and compliance exposure in this plan.')}>
                    Ask Legal
                  </button>
                </div>
                <div className="prompt-row">
                  <input
                    className="prompt-input"
                    value={prompt}
                    onChange={(event) => setPrompt(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        sendUserText(prompt)
                        setPrompt('')
                      }
                    }}
                    placeholder="Type your own prompt and press Enter..."
                  />
                  <button
                    className="btn send-btn"
                    onClick={() => {
                      sendUserText(prompt)
                      setPrompt('')
                    }}
                  >
                    Send
                  </button>
                </div>
              </div>
            </div>
          </motion.section>
        </div>

        <motion.aside className="panel" initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }}>
          <div className="panel-head">LIVE TRANSCRIPT</div>
          <div className="panel-body transcript">
            <AnimatePresence initial={false}>
              {mergedTranscript.map((entry) => (
                <motion.article
                  key={entry.id}
                  className="msg"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  layout
                >
                  <div className="msg-meta">
                    <span>{entry.speaker}</span>
                    <span>{new Date(entry.at).toLocaleTimeString()}</span>
                  </div>
                  <div className="msg-body">{entry.text}</div>
                </motion.article>
              ))}
            </AnimatePresence>
          </div>
        </motion.aside>
      </section>
    </main>
  )
}
