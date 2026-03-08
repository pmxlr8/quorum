import { useRef, useEffect, useState } from "react";
import { Send, Bot, User } from "lucide-react";
import type { TranscriptEntry, VoteItem, VoteValue } from "@/types/warroom";
import { Button } from "@/components/ui/button";
import { ThumbsUp, ThumbsDown, MinusCircle } from "lucide-react";

const roleColors: Record<string, string> = {
  chairperson: "bg-primary/8",
  analyst: "bg-success/8",
  advocate: "bg-warning/8",
  critic: "bg-destructive/8",
  secretary: "bg-secondary",
  creative: "bg-purple-500/8",
  technical: "bg-cyan-500/8",
  financial: "bg-emerald-500/8",
  custom: "bg-indigo-500/8",
};

const roleDotColors: Record<string, string> = {
  chairperson: "bg-primary",
  analyst: "bg-success",
  advocate: "bg-warning",
  critic: "bg-destructive",
  secretary: "bg-muted-foreground",
  creative: "bg-purple-500",
  technical: "bg-cyan-500",
  financial: "bg-emerald-500",
  custom: "bg-indigo-500",
};

interface ChatPanelProps {
  entries: TranscriptEntry[];
  vote: VoteItem | null;
  userVote?: VoteValue;
  onCastVote: (value: VoteValue) => void;
  onSendMessage?: (text: string) => void;
}

export function ChatPanel({ entries, vote, userVote, onCastVote, onSendMessage }: ChatPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [inputText, setInputText] = useState("");

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [entries, vote]);

  const handleSend = () => {
    if (inputText.trim() && onSendMessage) {
      onSendMessage(inputText.trim());
      setInputText("");
    }
  };

  return (
    <div className="flex flex-col h-full bg-card/50">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border flex items-center gap-2">
        <h3 className="text-sm font-medium text-foreground">Transcript</h3>
        <span className="ml-auto text-xs text-muted-foreground">{entries.length}</span>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {entries.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-3">
            <div className="w-12 h-12 rounded-2xl bg-secondary flex items-center justify-center">
              <Bot className="w-5 h-5 text-muted-foreground" />
            </div>
            <p className="text-sm text-muted-foreground text-center">
              Start a session to begin…
            </p>
          </div>
        )}

        {entries.map((entry) => {
          const isUser = entry.agentId === "user";
          const bubble = isUser ? "bg-primary/10" : (roleColors[entry.role] || "bg-secondary");
          const dot = isUser ? "bg-primary" : (roleDotColors[entry.role] || "bg-muted-foreground");

          return (
            <div key={entry.id} className="animate-fade-in">
              <div className="flex items-center gap-2 mb-1.5">
                {isUser ? (
                  <User className="w-3 h-3 text-primary" />
                ) : (
                  <span className={`w-2 h-2 rounded-full ${dot}`} />
                )}
                <span className={`text-xs font-medium ${isUser ? "text-primary" : "text-foreground"}`}>
                  {entry.agentName}
                </span>
                <span className="text-[11px] text-muted-foreground">
                  {new Date(entry.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
              </div>
              <div className={`ml-4 rounded-xl p-3 ${bubble}`}>
                <p className="text-[13px] text-foreground/90 leading-relaxed">{entry.text}</p>
              </div>
            </div>
          );
        })}

        {/* Vote card */}
        {vote && vote.status === "open" && (
          <div className="animate-fade-in ml-4">
            <div className="rounded-xl border border-border bg-card p-4 space-y-3 shadow-sm">
              <p className="text-xs font-medium text-muted-foreground">Vote Required</p>
              <p className="text-sm font-medium text-foreground">{vote.motion}</p>
              <div className="flex gap-2">
                <Button
                  variant="vote"
                  size="sm"
                  className={`flex-1 gap-1.5 rounded-lg ${userVote === "yes" ? "border-success bg-success/10 text-success" : ""}`}
                  onClick={() => onCastVote("yes")}
                >
                  <ThumbsUp className="w-3.5 h-3.5" />
                  Yes
                </Button>
                <Button
                  variant="vote"
                  size="sm"
                  className={`flex-1 gap-1.5 rounded-lg ${userVote === "no" ? "border-destructive bg-destructive/10 text-destructive" : ""}`}
                  onClick={() => onCastVote("no")}
                >
                  <ThumbsDown className="w-3.5 h-3.5" />
                  No
                </Button>
                <Button
                  variant="vote"
                  size="sm"
                  className={`flex-1 gap-1.5 rounded-lg ${userVote === "abstain" ? "border-muted-foreground bg-muted text-muted-foreground" : ""}`}
                  onClick={() => onCastVote("abstain")}
                >
                  <MinusCircle className="w-3.5 h-3.5" />
                  Pass
                </Button>
              </div>
              {Object.keys(vote.votes).length > 0 && (
                <div className="flex gap-0.5 h-1 rounded-full overflow-hidden bg-secondary">
                  {Object.values(vote.votes).filter(v => v === "yes").length > 0 && (
                    <div className="bg-success h-full rounded-full" style={{ flex: Object.values(vote.votes).filter(v => v === "yes").length }} />
                  )}
                  {Object.values(vote.votes).filter(v => v === "no").length > 0 && (
                    <div className="bg-destructive h-full rounded-full" style={{ flex: Object.values(vote.votes).filter(v => v === "no").length }} />
                  )}
                  {Object.values(vote.votes).filter(v => v === "abstain").length > 0 && (
                    <div className="bg-muted-foreground/40 h-full rounded-full" style={{ flex: Object.values(vote.votes).filter(v => v === "abstain").length }} />
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-3 border-t border-border">
        <div className="flex items-center gap-2 rounded-xl bg-secondary px-3 py-2.5">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Type a message…"
            className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none"
          />
          <button
            onClick={handleSend}
            className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-accent transition-colors"
          >
            <Send className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>
      </div>
    </div>
  );
}
