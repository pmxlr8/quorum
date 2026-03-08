import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useMemo, useState } from 'react';
import { useAudioPlayer } from '../hooks/useAudioPlayer';
import { useVoiceCapture } from '../hooks/useVoiceCapture';
import { useWsStore } from '../store/wsStore';
export function App() {
    const { connect, send, events, connected } = useWsStore();
    const [sessionId] = useState('local-session');
    const [isCapturing, setIsCapturing] = useState(false);
    useEffect(() => {
        connect(sessionId);
    }, [connect, sessionId]);
    const audioChunks = useMemo(() => events
        .filter((event) => event.type === 'audio_chunk')
        .map((event) => (event.type === 'audio_chunk' ? event.payload.data : ''))
        .filter(Boolean), [events]);
    useAudioPlayer(audioChunks);
    const voice = useVoiceCapture((data) => send({ type: 'audio', data }));
    return (_jsxs("main", { style: { background: '#0a0c11', color: '#fff', minHeight: '100vh', padding: '24px' }, children: [_jsx("h1", { children: "THE WAR ROOM" }), _jsxs("p", { children: ["WS: ", connected ? 'connected' : 'disconnected'] }), _jsxs("div", { style: { display: 'flex', gap: '8px', marginBottom: '16px' }, children: [_jsx("button", { onClick: async () => {
                            if (isCapturing)
                                return;
                            setIsCapturing(true);
                            await voice.start();
                        }, disabled: isCapturing, children: "Start Mic" }), _jsx("button", { onClick: () => {
                            if (!isCapturing)
                                return;
                            voice.stop();
                            send({ type: 'turn_complete' });
                            setIsCapturing(false);
                        }, disabled: !isCapturing, children: "Stop Mic" }), _jsx("button", { onClick: () => send({ type: 'text', text: 'What is the technical risk?' }), children: "Send Text Prompt" })] }), _jsxs("section", { children: [_jsx("h2", { children: "Events" }), _jsx("ul", { children: events.slice(-20).map((event, idx) => (_jsx("li", { children: _jsx("code", { children: event.type }) }, `${event.type}-${idx}`))) })] })] }));
}
