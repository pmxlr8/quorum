import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useMemo, useRef, useState } from 'react'

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
  initials: string
  color: string
  status: 'idle' | 'speaking' | 'thinking'
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

const AGENT_MAP: Record<AgentId, AgentView> = {
  alex_chen: { id: 'alex_chen', name: 'Alex Chen', role: 'CTO', initials: 'AC', color: '#4cc9f0', status: 'idle' },
  sarah_kim: { id: 'sarah_kim', name: 'Sarah Kim', role: 'CFO', initials: 'SK', color: '#ffd166', status: 'idle' },
  marcus_webb: { id: 'marcus_webb', name: 'Marcus Webb', role: 'Legal', initials: 'MW', color: '#ff6b6b', status: 'idle' },
  charon_orchestrator: { id: 'charon_orchestrator', name: 'Charon', role: 'Facilitator', initials: 'CH', color: '#20c997', status: 'idle' },
}

function parseSampleRate(mime: string | undefined): number {
  if (!mime) return 24000
  const match = mime.match(/rate=(\d+)/)
  return match ? parseInt(match[1], 10) : 24000
}

function mapSpeakerToAgent(speaker: string): { name: string; color: string } {
  if (speaker === 'you' || speaker === 'user') return { name: 'You', color: '#a78bfa' }
  if (speaker === 'system') return { name: 'System', color: '#6b7280' }
  if (speaker === 'assistant' || speaker === 'orchestrator') return { name: 'AI Board', color: '#20c997' }
  // Match against known agents
  for (const a of Object.values(AGENT_MAP)) {
    if (speaker.toLowerCase().includes(a.id) || speaker.toLowerCase().includes(a.name.toLowerCase())) {
      return { name: a.name, color: a.color }
    }
  }
  return { name: speaker, color: '#9eb1cf' }
}

function extractTranscript(event: ServerEvent): { speaker: string; text: string } | null {
  if (event.type === 'transcript_update') {
    return { speaker: event.payload.speaker, text: event.payload.text }
  }
  if (event.type === 'error') {
    return { speaker: 'system', text: event.payload.message }
  }
  return null
}

export function App() {
  const { connect, disconnect, send, events, connected } = useWsStore()
  const [sessionId] = useState('local-session')
  const [isCapturing, setIsCapturing] = useState(false)
  const [prompt, setPrompt] = useState('')
  const [localTranscript, setLocalTranscript] = useState<Array<{ id: string; at: number; speaker: string; text: string }>>([])
  const [health, setHealth] = useState<HealthInfo | null>(null)
  const transcriptEndRef = useRef<HTMLDivElement>(null)

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
        if (response.ok) {
          const data = (await response.json()) as HealthInfo
          if (alive) setHealth(data)
        }
      } catch { /* silent */ }
    }
    void loadHealth()
    const timer = setInterval(() => void loadHealth(), 10000)
    return () => { alive = false; clearInterval(timer) }
  }, [httpBase])

  const audioChunks = useMemo(
    () =>
      events
        .filter((entry) => entry.event.type === 'audio_chunk')
        .map((entry) => {
          if (entry.event.type !== 'audio_chunk') return { data: '', sampleRate: 24000 }
          return {
            data: entry.event.payload.data,
            sampleRate: parseSampleRate(entry.event.payload.mime),
          }
        })
        .filter((c) => c.data),
    [events],
  )

  const transcript = useMemo(
    () =>
      events
        .map((entry) => ({ id: entry.id, at: entry.at, data: extractTranscript(entry.event) }))
        .filter((entry): entry is { id: string; at: number; data: { speaker: string; text: string } } => Boolean(entry.data)),
    [events],
  )

  const mergedTranscript = useMemo(() => {
    const sorted = [...transcript.map((entry) => ({ ...entry.data, id: entry.id, at: entry.at })), ...localTranscript]
      .sort((a, b) => a.at - b.at)
      .slice(-80)

    // Merge consecutive entries from the same speaker
    const merged: typeof sorted = []
    for (const entry of sorted) {
      const prev = merged[merged.length - 1]
      if (prev && prev.speaker === entry.speaker && entry.at - prev.at < 30000) {
        // Same speaker within 30s — append text
        prev.text = prev.text + ' ' + entry.text
        prev.id = entry.id // Use latest id for React key stability
      } else {
        merged.push({ ...entry })
      }
    }
    return merged.slice(-50)
  }, [localTranscript, transcript])

  // Find which agent is currently speaking — reset on turn_complete
  const currentSpeaker = useMemo(() => {
    // Walk events from newest to oldest. If we hit turn_complete before agent_speaking, no one is speaking.
    for (let i = events.length - 1; i >= 0; i--) {
      const ev = events[i].event
      if (ev.type === 'turn_complete') return null
      if (ev.type === 'agent_speaking') return ev.payload.agent as AgentId
    }
    return null
  }, [events])

  const agents = useMemo(() =>
    Object.values(AGENT_MAP).map((a) => ({
      ...a,
      status: (currentSpeaker === a.id ? 'speaking' : 'idle') as AgentView['status'],
    })),
    [currentSpeaker],
  )

  useAudioPlayer(audioChunks)

  // Auto-scroll transcript
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [mergedTranscript])

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

  const liveMode = health?.live_client_ready ?? false

  return (
    <main className="warroom-root">
      {/* ──── Header ──── */}
      <header className="topbar">
        <div className="title-wrap">
          <div className="logo-icon">⚡</div>
          <div>
            <h1 className="title">Virtual War Room</h1>
            <span className="subtitle">AI Board of Directors</span>
          </div>
        </div>
        <div className="topbar-right">
          <div className={`status-chip ${liveMode ? 'live' : 'demo'}`}>
            <span className={`dot ${liveMode ? 'green' : 'amber'}`} />
            {liveMode ? 'LIVE' : 'DEMO'}
          </div>
          <div className={`status-chip ${connected ? 'connected' : 'disconnected'}`}>
            <span className={`dot ${connected ? 'green' : 'red'}`} />
            {connected ? 'Connected' : 'Offline'}
          </div>
        </div>
      </header>

      {/* ──── Mission Banner ──── */}
      <section className="mission-bar">
        <span className="mission-label">AGENDA</span>
        <span className="mission-text">Decide the next product milestone — deliver clear Decision, Risks, and Owner.</span>
      </section>

      {/* ──── Main Layout ──── */}
      <section className="layout">
        {/* Left: Board Members */}
        <aside className="panel board-panel">
          <div className="panel-head">Board Members</div>
          <div className="agent-list">
            {agents.map((agent) => (
              <motion.div
                key={agent.id}
                className={`agent-card ${agent.status}`}
                layout
                animate={{
                  borderColor: agent.status === 'speaking' ? agent.color : 'rgba(255,255,255,0.08)',
                }}
              >
                <div className="agent-avatar" style={{ background: agent.color }}>
                  {agent.initials}
                </div>
                <div className="agent-info">
                  <div className="agent-name">{agent.name}</div>
                  <div className="agent-role">{agent.role}</div>
                </div>
                {agent.status === 'speaking' && (
                  <motion.div
                    className="speaking-indicator"
                    animate={{ scale: [1, 1.3, 1] }}
                    transition={{ repeat: Infinity, duration: 1 }}
                  >
                    <div className="wave-bar" />
                    <div className="wave-bar" style={{ animationDelay: '0.15s' }} />
                    <div className="wave-bar" style={{ animationDelay: '0.3s' }} />
                  </motion.div>
                )}
                {agent.status === 'idle' && <span className="idle-tag">Ready</span>}
              </motion.div>
            ))}
          </div>

          {/* Quick action buttons */}
          <div className="quick-actions">
            <button className="action-btn cto" onClick={() => sendUserText('What are the key technical risks and architecture concerns we should address?')}>
              <span className="action-avatar" style={{ background: '#4cc9f0' }}>AC</span>
              Ask CTO
            </button>
            <button className="action-btn cfo" onClick={() => sendUserText('What does the financial picture look like? Budget, runway, and ROI projections?')}>
              <span className="action-avatar" style={{ background: '#ffd166' }}>SK</span>
              Ask CFO
            </button>
            <button className="action-btn legal" onClick={() => sendUserText('Are there any legal risks, compliance concerns, or liability exposure here?')}>
              <span className="action-avatar" style={{ background: '#ff6b6b' }}>MW</span>
              Ask Legal
            </button>
          </div>
        </aside>

        {/* Center: Controls + Input */}
        <div className="center-col">
          {/* Mic Control */}
          <div className="mic-section">
            <motion.button
              className={`mic-orb ${isCapturing ? 'active' : ''}`}
              whileTap={{ scale: 0.95 }}
              onClick={async () => {
                if (isCapturing) {
                  voice.stop()
                  send({ type: 'turn_complete' })
                  setIsCapturing(false)
                  return
                }
                try {
                  setIsCapturing(true)
                  await voice.start()
                  addLocalEntry('you', '🎙️ Listening...')
                } catch (error) {
                  setIsCapturing(false)
                  const detail = error instanceof Error ? error.message : 'Microphone error'
                  addLocalEntry('system', `Mic failed: ${detail}`)
                }
              }}
            >
              {isCapturing ? (
                <div className="mic-icon recording">
                  <div className="pulse-ring" />
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
                </div>
              ) : (
                <div className="mic-icon">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                    <line x1="12" y1="19" x2="12" y2="23"/>
                    <line x1="8" y1="23" x2="16" y2="23"/>
                  </svg>
                </div>
              )}
            </motion.button>
            <div className="mic-label">{isCapturing ? 'Tap to stop' : 'Tap to speak'}</div>
          </div>

          {/* Text Input */}
          <div className="input-section">
            <input
              className="chat-input"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && prompt.trim()) {
                  sendUserText(prompt)
                  setPrompt('')
                }
              }}
              placeholder="Ask your board anything..."
            />
            <button
              className="send-btn"
              disabled={!prompt.trim()}
              onClick={() => {
                if (prompt.trim()) {
                  sendUserText(prompt)
                  setPrompt('')
                }
              }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
            </button>
          </div>

          {!liveMode && (
            <div className="demo-notice">
              Demo mode — text responses use local AI. Voice requires Vertex AI credentials.
            </div>
          )}
        </div>

        {/* Right: Transcript */}
        <aside className="panel transcript-panel">
          <div className="panel-head">Live Transcript</div>
          <div className="transcript-body">
            <AnimatePresence initial={false}>
              {mergedTranscript.map((entry) => {
                const mapped = mapSpeakerToAgent(entry.speaker)
                const isUser = entry.speaker === 'you' || entry.speaker === 'user'
                return (
                  <motion.div
                    key={entry.id}
                    className={`msg ${isUser ? 'msg-user' : ''} ${entry.speaker === 'system' ? 'msg-system' : ''}`}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    layout
                  >
                    <div className="msg-header">
                      <span className="msg-speaker" style={{ color: mapped.color }}>{mapped.name}</span>
                      <span className="msg-time">{new Date(entry.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                    </div>
                    <div className="msg-text">{entry.text}</div>
                  </motion.div>
                )
              })}
            </AnimatePresence>
            <div ref={transcriptEndRef} />
          </div>
        </aside>
      </section>
    </main>
  )
}
