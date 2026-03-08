import { useRef, useEffect } from "react";
import type { TranscriptEntry } from "@/types/warroom";

const roleColors: Record<string, string> = {
  chairperson: "text-accent",
  analyst: "text-glow-info",
  advocate: "text-primary",
  critic: "text-destructive",
  secretary: "text-muted-foreground",
};

export function TranscriptPanel({ entries }: { entries: TranscriptEntry[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [entries]);

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-2.5 border-b border-border flex items-center gap-2">
        <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
        <h3 className="text-xs font-semibold uppercase tracking-widest font-mono text-muted-foreground">
          Transcript
        </h3>
        <span className="ml-auto text-[10px] font-mono text-muted-foreground">{entries.length} entries</span>
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3 scan-line">
        {entries.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <p className="text-sm text-muted-foreground font-mono">Awaiting session start...</p>
          </div>
        )}
        {entries.map((entry) => (
          <div key={entry.id} className="group">
            <div className="flex items-baseline gap-2 mb-0.5">
              <span className={`text-xs font-semibold ${roleColors[entry.role] || "text-foreground"}`}>
                {entry.agentName}
              </span>
              <span className="text-[10px] font-mono text-muted-foreground">
                {new Date(entry.timestamp).toLocaleTimeString()}
              </span>
            </div>
            <p className="text-sm text-foreground/90 leading-relaxed pl-0 border-l-2 border-border group-hover:border-primary/30 pl-3 transition-colors">
              {entry.text}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
