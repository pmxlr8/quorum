import { create } from 'zustand';
const wsBase = import.meta.env.VITE_WS_BASE_URL ?? 'ws://localhost:8000';
export const useWsStore = create((set, get) => ({
    socket: null,
    connected: false,
    retries: 0,
    events: [],
    connect: (sessionId) => {
        const url = `${wsBase}/ws/${sessionId}`;
        const socket = new WebSocket(url);
        socket.onopen = () => set({ connected: true, retries: 0 });
        socket.onmessage = (msg) => {
            const payload = JSON.parse(msg.data);
            set((state) => ({ events: [...state.events, payload] }));
        };
        socket.onclose = () => {
            const retries = get().retries + 1;
            set({ connected: false, retries });
            if (retries <= 5) {
                const delay = Math.min(1000 * 2 ** (retries - 1), 8000);
                setTimeout(() => get().connect(sessionId), delay);
            }
        };
        set({ socket });
    },
    send: (event) => {
        const socket = get().socket;
        if (socket?.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(event));
        }
    },
}));
