import { useEffect, useRef } from 'react';
export function useAudioPlayer(base64PcmChunks) {
    const contextRef = useRef(null);
    const queueRef = useRef([]);
    const playingRef = useRef(false);
    useEffect(() => {
        if (!contextRef.current) {
            contextRef.current = new AudioContext({ sampleRate: 16000 });
        }
    }, []);
    useEffect(() => {
        for (const chunk of base64PcmChunks) {
            const bytes = Uint8Array.from(atob(chunk), (ch) => ch.charCodeAt(0));
            const pcm = new Int16Array(bytes.buffer);
            const float = new Float32Array(pcm.length);
            for (let i = 0; i < pcm.length; i += 1) {
                float[i] = pcm[i] / 32768;
            }
            queueRef.current.push(float);
        }
        const playNext = () => {
            if (playingRef.current)
                return;
            const ctx = contextRef.current;
            if (!ctx)
                return;
            const next = queueRef.current.shift();
            if (!next)
                return;
            playingRef.current = true;
            const buffer = ctx.createBuffer(1, next.length, 16000);
            buffer.getChannelData(0).set(next);
            const src = ctx.createBufferSource();
            src.buffer = buffer;
            src.connect(ctx.destination);
            src.onended = () => {
                playingRef.current = false;
                playNext();
            };
            src.start();
        };
        playNext();
    }, [base64PcmChunks]);
}
