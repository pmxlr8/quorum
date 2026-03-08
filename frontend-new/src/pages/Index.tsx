import { useState, useCallback, useRef, useEffect } from "react";
import type { WarRoomState, VoteValue, TranscriptEntry, Agent, VoteItem } from "@/types/warroom";
import { StatusBar } from "@/components/warroom/StatusBar";
import { VoiceControls } from "@/components/warroom/VoiceControls";
import { WarTable } from "@/components/warroom/WarTable";
import { ChatPanel } from "@/components/warroom/ChatPanel";
import { LeftSidebar } from "@/components/warroom/LeftSidebar";
import { ThemeToggle } from "@/components/ThemeToggle";
import { SessionSetupDialog, type SessionConfig } from "@/components/warroom/SessionSetupDialog";
import { useWarRoomSocket, type ServerMessage } from "@/hooks/useWarRoomSocket";
import { MicCapture, AudioPlayer } from "@/hooks/useAudio";

// Default background image URL — swap from backend later
export const DEFAULT_BG_IMAGE = "";

export default function WarRoom() {
  const [state, setState] = useState<WarRoomState>({
    sessionStatus: "idle",
    agents: [],
    transcript: [],
    currentVote: null,
    documents: [],
    isMicActive: false,
    isSpeakerActive: true,
  });
  const [userVote, setUserVote] = useState<VoteValue | undefined>();
  const [sessionSeconds, setSessionSeconds] = useState(0);
  const [intervalId, setIntervalId] = useState<ReturnType<typeof setInterval> | null>(null);
  const [isHandRaised, setIsHandRaised] = useState(false);
  const [showSetup, setShowSetup] = useState(false);
  const [sessionAgenda, setSessionAgenda] = useState("");
  const [bgImage, setBgImage] = useState(DEFAULT_BG_IMAGE);

  // Audio refs
  const micRef = useRef<MicCapture | null>(null);
  const playerRef = useRef<AudioPlayer | null>(null);

  // Initialize audio player on mount
  useEffect(() => {
    playerRef.current = new AudioPlayer();
    return () => {
      playerRef.current?.close();
    };
  }, []);

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m.toString().padStart(2, "0")}:${sec.toString().padStart(2, "0")}`;
  };

  // ── WebSocket message handler ─────────────────────────────────────────────

  const handleServerMessage = useCallback((msg: ServerMessage) => {
    switch (msg.type) {
      case "session.ready": {
        const agents = (msg.agents as Agent[]) || [];
        setState((prev) => ({
          ...prev,
          sessionStatus: "active",
          agents,
        }));
        break;
      }

      case "agent.state": {
        const agentId = msg.agentId as string;
        const speakingState = msg.speakingState as Agent["speakingState"];
        setState((prev) => ({
          ...prev,
          agents: prev.agents.map((a) =>
            a.id === agentId ? { ...a, speakingState } : a
          ),
        }));
        break;
      }

      case "transcript.add": {
        const entry = msg.entry as TranscriptEntry;
        setState((prev) => ({
          ...prev,
          transcript: [...prev.transcript, entry],
        }));
        break;
      }

      case "audio.chunk": {
        // Play incoming audio from agents
        if (playerRef.current) {
          playerRef.current.enqueue(msg.data as string);
        }
        break;
      }

      case "vote.proposed": {
        const vote = msg.vote as VoteItem;
        setState((prev) => ({ ...prev, currentVote: vote }));
        setUserVote(undefined);
        break;
      }

      case "vote.update": {
        const vote = msg.vote as VoteItem;
        setState((prev) => ({ ...prev, currentVote: vote }));
        break;
      }

      case "document.status": {
        const docId = msg.docId as string;
        const status = msg.status as string;
        const summary = msg.summary as string | undefined;
        setState((prev) => ({
          ...prev,
          documents: prev.documents.map((d) =>
            d.id === docId ? { ...d, status: status as any, summary } : d
          ),
        }));
        break;
      }

      case "session.error": {
        console.error("[Server Error]", msg.message);
        setState((prev) => ({ ...prev, sessionStatus: "error" }));
        break;
      }

      case "session.ended": {
        setState((prev) => ({
          ...prev,
          sessionStatus: "ended",
          agents: prev.agents.map((a) => ({ ...a, speakingState: "idle" as const })),
        }));
        break;
      }

      default:
        console.log("[WS] Unhandled message type:", msg.type, msg);
    }
  }, []);

  const { connect, disconnect, send, sendAudioChunk } = useWarRoomSocket(handleServerMessage);

  // ── Session lifecycle ─────────────────────────────────────────────────────

  const handleSessionConfig = useCallback((config: SessionConfig) => {
    setShowSetup(false);
    setSessionAgenda(config.agenda);

    // Connect to WebSocket and create session
    setState((prev) => ({ ...prev, sessionStatus: "connecting" }));
    connect();

    // Give WS a moment to connect, then send session.create
    setTimeout(() => {
      send({
        type: "session.create",
        config: {
          agenda: config.agenda,
          selectedAgentIds: config.selectedAgentIds,
        },
      });
    }, 500);

    // Start timer
    setSessionSeconds(0);
    const id = setInterval(() => setSessionSeconds((s) => s + 1), 1000);
    setIntervalId(id);
  }, [connect, send]);

  const handleStartSession = useCallback(() => {
    setShowSetup(true);
  }, []);

  const handleEndSession = useCallback(() => {
    // Stop mic
    if (micRef.current) {
      micRef.current.stop();
      micRef.current = null;
    }
    playerRef.current?.flush();

    setState((prev) => ({
      ...prev,
      sessionStatus: "ended",
      isMicActive: false,
      agents: prev.agents.map((a) => ({ ...a, speakingState: "idle" as const })),
    }));
    if (intervalId) clearInterval(intervalId);
    disconnect();
  }, [intervalId, disconnect]);

  // ── Voice controls ────────────────────────────────────────────────────────

  const handleToggleMic = useCallback(async () => {
    if (state.sessionStatus !== "active") return;

    if (!state.isMicActive) {
      // Turn on mic
      try {
        const mic = new MicCapture();
        mic.onChunk = (b64) => {
          sendAudioChunk(b64);
        };
        await mic.start();
        micRef.current = mic;
        setState((prev) => ({ ...prev, isMicActive: true }));
      } catch (err) {
        console.error("Mic access denied:", err);
      }
    } else {
      // Turn off mic
      if (micRef.current) {
        micRef.current.stop();
        micRef.current = null;
      }
      send({ type: "audio.stop" });
      setState((prev) => ({ ...prev, isMicActive: false }));
    }
  }, [state.isMicActive, state.sessionStatus, sendAudioChunk, send]);

  const handleToggleSpeaker = useCallback(() => {
    setState((prev) => {
      const newState = !prev.isSpeakerActive;
      if (playerRef.current) {
        playerRef.current.muted = !newState;
      }
      return { ...prev, isSpeakerActive: newState };
    });
  }, []);

  // ── Chat / text ───────────────────────────────────────────────────────────

  const handleCastVote = useCallback((value: VoteValue) => {
    setUserVote(value);
    setState((prev) => ({
      ...prev,
      currentVote: prev.currentVote
        ? { ...prev.currentVote, votes: { ...prev.currentVote.votes, user: value } }
        : null,
    }));
    if (state.currentVote) {
      send({ type: "vote.cast", voteId: state.currentVote.id, value });
    }
  }, [send, state.currentVote]);

  const handleUpload = useCallback((file: File) => {
    const docId = `doc-${Date.now()}`;
    setState((prev) => ({
      ...prev,
      documents: [...prev.documents, { id: docId, name: file.name, status: "uploading" }],
    }));

    // Read file and send to backend
    const reader = new FileReader();
    reader.onload = () => {
      const b64 = (reader.result as string).split(",")[1] || "";
      send({
        type: "document.upload",
        name: file.name,
        data: b64,
        mimeType: file.type || "application/octet-stream",
      });
    };
    reader.readAsDataURL(file);
  }, [send]);

  const handleUserMessage = useCallback((text: string) => {
    send({ type: "text.send", text });
  }, [send]);

  const handleRaiseHand = useCallback(() => {
    setIsHandRaised((h) => {
      if (!h) {
        send({ type: "hand.raise" });
      }
      return !h;
    });
  }, [send]);

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      <LeftSidebar currentAgents={state.agents} />

      {/* Title bar */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-border bg-card">
        <div className="flex items-center gap-3 ml-12">
          <div className="w-8 h-8 rounded-xl bg-primary flex items-center justify-center shadow-sm">
            <span className="text-primary-foreground font-semibold text-sm">Q</span>
          </div>
          <div>
            <h1 className="text-sm font-semibold text-foreground tracking-tight">Quorum</h1>
            <p className="text-[11px] text-muted-foreground">Virtual War Room</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {sessionAgenda && (
            <p className="hidden lg:block text-[12px] text-muted-foreground truncate max-w-xs">
              {sessionAgenda}
            </p>
          )}
          <ThemeToggle />
        </div>
      </div>

      <StatusBar
        status={state.sessionStatus}
        agentCount={state.agents.length}
        sessionTime={formatTime(sessionSeconds)}
      />

      {/* Main layout */}
      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 flex flex-col min-w-0">
          <WarTable
            agents={state.agents}
            documents={state.documents}
            onUpload={handleUpload}
            sessionStatus={state.sessionStatus}
            bgImage={bgImage}
          />
          <VoiceControls
            isMicActive={state.isMicActive}
            isSpeakerActive={state.isSpeakerActive}
            isHandRaised={isHandRaised}
            sessionActive={state.sessionStatus === "active"}
            onToggleMic={handleToggleMic}
            onToggleSpeaker={handleToggleSpeaker}
            onRaiseHand={handleRaiseHand}
            onStartSession={handleStartSession}
            onEndSession={handleEndSession}
          />
        </div>

        <div className="w-80 border-l border-border shrink-0">
          <ChatPanel
            entries={state.transcript}
            vote={state.currentVote}
            userVote={userVote}
            onCastVote={handleCastVote}
            onSendMessage={handleUserMessage}
          />
        </div>
      </div>

      <SessionSetupDialog
        open={showSetup}
        onStart={handleSessionConfig}
        onCancel={() => setShowSetup(false)}
      />
    </div>
  );
}
