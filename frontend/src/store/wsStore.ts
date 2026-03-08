import { create } from 'zustand'
import type { ClientEvent, ServerEvent } from '../types/events'

export type EventLogEntry = {
  id: string
  at: number
  event: ServerEvent
}

type WsState = {
  socket: WebSocket | null
  sessionId: string | null
  connected: boolean
  retries: number
  manualClose: boolean
  outboundQueue: ClientEvent[]
  events: EventLogEntry[]
  connect: (sessionId: string) => void
  disconnect: () => void
  send: (event: ClientEvent) => void
}

const wsBase = import.meta.env.VITE_WS_BASE_URL ?? 'ws://localhost:8000'

export const useWsStore = create<WsState>((set, get) => ({
  socket: null,
  sessionId: null,
  connected: false,
  retries: 0,
  manualClose: false,
  outboundQueue: [],
  events: [],
  connect: (sessionId: string) => {
    const current = get().socket
    const currentSession = get().sessionId
    if (
      current &&
      currentSession === sessionId &&
      (current.readyState === WebSocket.OPEN || current.readyState === WebSocket.CONNECTING)
    ) {
      return
    }
    if (current && current.readyState < WebSocket.CLOSING) {
      current.close(1000, 'reconnect')
    }

    const url = `${wsBase}/ws/${sessionId}`
    const socket = new WebSocket(url)

    socket.onopen = () => {
      if (get().socket !== socket) return
      const queued = get().outboundQueue
      for (const item of queued) {
        socket.send(JSON.stringify(item))
      }
      set({ connected: true, retries: 0, outboundQueue: [] })
    }
    socket.onmessage = (msg: MessageEvent<string>) => {
      if (get().socket !== socket) return
      let payload: ServerEvent
      try {
        payload = JSON.parse(msg.data) as ServerEvent
      } catch {
        payload = { type: 'error', payload: { message: 'Invalid server event payload' } }
      }
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
      set((state) => ({ events: [...state.events, { id, at: Date.now(), event: payload }] }))
    }
    socket.onclose = () => {
      if (get().socket !== socket) return
      if (get().manualClose) {
        set({ connected: false, socket: null })
        return
      }
      const retries = get().retries + 1
      set({ connected: false, retries, socket: null })
      if (retries <= 5) {
        const delay = Math.min(1000 * 2 ** (retries - 1), 8000)
        setTimeout(() => {
          if (!get().manualClose) {
            get().connect(sessionId)
          }
        }, delay)
      }
    }

    set({ socket, sessionId, manualClose: false })
  },
  disconnect: () => {
    set({ manualClose: true, connected: false, retries: 0 })
    const socket = get().socket
    if (socket && socket.readyState < WebSocket.CLOSING) {
      socket.close(1000, 'user disconnect')
    }
    set({ socket: null })
  },
  send: (event: ClientEvent) => {
    const socket = get().socket
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(event))
      return
    }
    set((state) => ({
      outboundQueue: [...state.outboundQueue, event].slice(-200),
    }))
  },
}))
