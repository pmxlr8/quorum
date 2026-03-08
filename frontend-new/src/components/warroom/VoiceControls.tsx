import { Mic, MicOff, Volume2, VolumeX, Hand, Play, Square } from "lucide-react";
import { Button } from "@/components/ui/button";

interface VoiceControlsProps {
  isMicActive: boolean;
  isSpeakerActive: boolean;
  isHandRaised: boolean;
  sessionActive: boolean;
  onToggleMic: () => void;
  onToggleSpeaker: () => void;
  onRaiseHand: () => void;
  onStartSession: () => void;
  onEndSession: () => void;
}

export function VoiceControls({
  isMicActive,
  isSpeakerActive,
  isHandRaised,
  sessionActive,
  onToggleMic,
  onToggleSpeaker,
  onRaiseHand,
  onStartSession,
  onEndSession,
}: VoiceControlsProps) {
  return (
    <div className="flex items-center gap-3 px-5 py-3 border-t border-border bg-card">
      {!sessionActive ? (
        <Button variant="tactical" size="sm" onClick={onStartSession} className="gap-2">
          <Play className="w-3.5 h-3.5" />
          Start Session
        </Button>
      ) : (
        <Button variant="danger" size="sm" onClick={onEndSession} className="gap-2">
          <Square className="w-3 h-3" />
          End
        </Button>
      )}

      <div className="flex-1" />

      <Button
        variant={isHandRaised ? "default" : "ghost"}
        size="icon"
        onClick={onRaiseHand}
        disabled={!sessionActive}
        className="rounded-full"
      >
        <Hand className="w-4 h-4" />
      </Button>

      <Button
        variant="ghost"
        size="icon"
        onClick={onToggleSpeaker}
        disabled={!sessionActive}
        className="rounded-full"
      >
        {isSpeakerActive ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4 text-destructive" />}
      </Button>

      <button
        onClick={onToggleMic}
        disabled={!sessionActive}
        className={`w-12 h-12 rounded-full flex items-center justify-center transition-all duration-200 disabled:opacity-40 ${
          isMicActive
            ? "bg-primary text-primary-foreground shadow-lg shadow-primary/25 scale-105"
            : "bg-secondary text-muted-foreground hover:bg-accent"
        }`}
      >
        {isMicActive ? <Mic className="w-5 h-5" /> : <MicOff className="w-5 h-5" />}
      </button>
    </div>
  );
}
