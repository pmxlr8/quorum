import { Wifi, WifiOff, Clock, Users } from "lucide-react";
import type { SessionStatus } from "@/types/warroom";

interface StatusBarProps {
  status: SessionStatus;
  agentCount: number;
  sessionTime: string;
}

const statusConfig: Record<SessionStatus, { label: string; dotColor: string; textColor: string }> = {
  idle: { label: "Standby", dotColor: "bg-muted-foreground", textColor: "text-muted-foreground" },
  connecting: { label: "Connecting", dotColor: "bg-warning", textColor: "text-warning" },
  active: { label: "Live", dotColor: "bg-success", textColor: "text-success" },
  error: { label: "Error", dotColor: "bg-destructive", textColor: "text-destructive" },
  ended: { label: "Ended", dotColor: "bg-muted-foreground", textColor: "text-muted-foreground" },
};

export function StatusBar({ status, agentCount, sessionTime }: StatusBarProps) {
  const config = statusConfig[status];

  return (
    <div className="flex items-center justify-between px-5 py-2 border-b border-border bg-card/50 text-xs">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          {status === "active" ? (
            <Wifi className="w-3.5 h-3.5 text-success" />
          ) : (
            <WifiOff className="w-3.5 h-3.5 text-muted-foreground" />
          )}
          <div className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${config.dotColor} ${status === "active" ? "animate-gentle-pulse" : ""}`} />
            <span className={`font-medium ${config.textColor}`}>
              {config.label}
            </span>
          </div>
        </div>
        <span className="w-px h-3.5 bg-border" />
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <Users className="w-3.5 h-3.5" />
          <span>{agentCount} agents</span>
        </div>
      </div>
      <div className="flex items-center gap-1.5 text-muted-foreground">
        <Clock className="w-3.5 h-3.5" />
        <span className="font-mono text-xs">{sessionTime}</span>
      </div>
    </div>
  );
}
