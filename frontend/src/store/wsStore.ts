import { create } from 'zustand'
import type { ClientEvent, ServerEvent } from '../types/events'

type WsState = {
  socket: WebSocket | null
  connected: boolean
  retries: number
  events: ServerEvent[]
  connect: (sessionId: string) => void
  send: (event: ClientEvent) => void
}

const wsBase = import.meta.env.VITE_WS_BASE_URL ?? 'ws://localhost:8000'

export const useWsStore = create<WsState>((set, get) => ({
  socket: null,
  connected: false,
  retries: 0,
  events: [],
  connect: (sessionId: string) => {
    const url = `${wsBase}/ws/${sessionId}`
    const socket = new WebSocket(url)

    socket.onopen = () => set({ connected: true, retries: 0 })
    socket.onmessage = (msg: MessageEvent<string>) => {
      const payload = JSON.parse(msg.data) as ServerEvent
      set((state) => ({ events: [...state.events, payload] }))
    }
    socket.onclose = () => {
      const retries = get().retries + 1
      set({ connected: false, retries })
      if (retries <= 5) {
        const delay = Math.min(1000 * 2 ** (retries - 1), 8000)
        setTimeout(() => get().connect(sessionId), delay)
      }
    }

    set({ socket })
  },
  send: (event: ClientEvent) => {
    const socket = get().socket
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(event))
    }
  },
}))
