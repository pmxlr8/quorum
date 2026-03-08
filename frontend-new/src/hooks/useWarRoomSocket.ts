/**
 * WebSocket hook for Quorum War Room.
 *
 * Manages the WebSocket connection to the backend and provides
 * methods to send/receive messages. Queues messages until connected.
 */

import { useRef, useCallback, useEffect } from "react";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws";

export type ServerMessage = {
  type: string;
  [key: string]: unknown;
};

export type MessageHandler = (msg: ServerMessage) => void;

export function useWarRoomSocket(onMessage: MessageHandler) {
  const wsRef = useRef<WebSocket | null>(null);
  const handlersRef = useRef<MessageHandler>(onMessage);
  const pendingQueue = useRef<string[]>([]);

  // Keep handler ref current
  useEffect(() => {
    handlersRef.current = onMessage;
  }, [onMessage]);

  const flushQueue = useCallback((ws: WebSocket) => {
    while (pendingQueue.current.length > 0) {
      const item = pendingQueue.current.shift()!;
      console.log("[WS] Flushing queued message:", item.substring(0, 80));
      ws.send(item);
    }
  }, []);

  const connect = useCallback(() => {
    // Already open — just flush any pending
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      flushQueue(wsRef.current);
      return;
    }
    // Already connecting — let onopen handle it
    if (wsRef.current?.readyState === WebSocket.CONNECTING) return;

    console.log("[WS] Connecting to", WS_URL);
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      console.log("[WS] Connected to", WS_URL);
      flushQueue(ws);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as ServerMessage;
        handlersRef.current(msg);
      } catch (err) {
        console.error("[WS] Failed to parse message:", err);
      }
    };

    ws.onerror = (err) => {
      console.error("[WS] Error:", err);
    };

    ws.onclose = (event) => {
      console.log("[WS] Disconnected:", event.code, event.reason);
      if (wsRef.current === ws) wsRef.current = null;
    };

    wsRef.current = ws;
  }, [flushQueue]);

  const disconnect = useCallback(() => {
    pendingQueue.current = [];
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const send = useCallback((msg: Record<string, unknown>) => {
    const payload = JSON.stringify(msg);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(payload);
    } else {
      // Queue it — will be flushed when onopen fires
      console.log("[WS] Queuing message (not yet open):", msg.type);
      pendingQueue.current.push(payload);
    }
  }, []);

  const sendAudioChunk = useCallback((b64data: string) => {
    // Audio is fire-and-forget — don't queue, just drop if not connected
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "audio.chunk", data: b64data }));
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      wsRef.current?.close();
    };
  }, []);

  return { connect, disconnect, send, sendAudioChunk, wsRef };
}
