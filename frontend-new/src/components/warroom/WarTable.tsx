import { useRef } from "react";
import type { Agent, UploadedDocument } from "@/types/warroom";
import { FileText, Loader2, CheckCircle, AlertCircle, Upload } from "lucide-react";

const roleInitials: Record<string, string> = {
  chairperson: "CH",
  analyst: "AN",
  advocate: "AD",
  critic: "CR",
  secretary: "SC",
  creative: "CV",
  technical: "TE",
  financial: "FN",
  custom: "CU",
};

const roleLabel: Record<string, string> = {
  chairperson: "Chairperson",
  analyst: "Analyst",
  advocate: "Advocate",
  critic: "Critic",
  secretary: "Secretary",
  creative: "Creative",
  technical: "Technical",
  financial: "Financial",
  custom: "Custom",
};

const roleColor: Record<string, string> = {
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

function getInitials(name: string, role: string): string {
  if (roleInitials[role]) return roleInitials[role];
  return name.slice(0, 2).toUpperCase();
}

const statusIcons: Record<string, React.ReactNode> = {
  uploading: <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground" />,
  processing: <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />,
  analyzed: <CheckCircle className="w-3.5 h-3.5 text-success" />,
  error: <AlertCircle className="w-3.5 h-3.5 text-destructive" />,
};

interface WarTableProps {
  agents: Agent[];
  documents: UploadedDocument[];
  onUpload: (file: File) => void;
  sessionStatus: string;
  bgImage?: string;
}

export function WarTable({ agents, documents, onUpload, sessionStatus, bgImage }: WarTableProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const agentPositions = agents.map((_, i) => {
    const angleStep = (Math.PI * 2) / agents.length;
    const a = angleStep * i - Math.PI / 2;
    const radiusPercent = 32;
    return {
      left: `${50 + radiusPercent * Math.cos(a)}%`,
      top: `${50 + radiusPercent * Math.sin(a)}%`,
    };
  });

  return (
    <div className="flex-1 flex flex-col min-h-0 relative">
      {/* War table area */}
      <div className="flex-1 relative overflow-hidden bg-background">
        {/* Optional background image from backend */}
        {bgImage && (
          <div
            className="absolute inset-0 bg-cover bg-center opacity-10 pointer-events-none"
            style={{ backgroundImage: `url(${bgImage})` }}
          />
        )}

        {/* Subtle concentric rings */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="absolute rounded-full border border-border/40"
              style={{ width: `${i * 22}%`, height: `${i * 22}%` }}
            />
          ))}
        </div>

        {/* Center logo */}
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-0">
          <div className="w-16 h-16 rounded-2xl bg-secondary flex items-center justify-center">
            <span className="text-xl font-semibold text-muted-foreground/40">Q</span>
          </div>
        </div>

        {/* Empty state */}
        {agents.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="text-sm text-muted-foreground">Start a session to see agents here</p>
          </div>
        )}

        {/* Agents */}
        {agents.map((agent, i) => {
          const isSpeaking = agent.speakingState === "speaking";
          const color = roleColor[agent.role] || "bg-muted-foreground";

          return (
            <div
              key={agent.id}
              className="absolute -translate-x-1/2 -translate-y-1/2 flex flex-col items-center gap-2 z-10 transition-all duration-500"
              style={{ left: agentPositions[i].left, top: agentPositions[i].top }}
            >
              <div className="relative">
                {/* Avatar or initials */}
                {agent.avatar ? (
                  <img
                    src={agent.avatar}
                    alt={agent.name}
                    className={`w-14 h-14 rounded-2xl object-cover transition-all duration-300 shadow-sm ${
                      isSpeaking ? "shadow-lg scale-105 ring-2 ring-primary/40" : "border border-border"
                    }`}
                  />
                ) : (
                  <div
                    className={`w-14 h-14 rounded-2xl flex items-center justify-center text-sm font-semibold transition-all duration-300 shadow-sm ${
                      isSpeaking
                        ? `${color} text-primary-foreground shadow-lg scale-105`
                        : "bg-card text-foreground border border-border"
                    }`}
                  >
                    {getInitials(agent.name, agent.role)}
                  </div>
                )}
                {isSpeaking && (
                  <div className="absolute inset-0 rounded-2xl border-2 border-primary/30 animate-pulse-ring" />
                )}
                {isSpeaking && (
                  <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-success border-2 border-background" />
                )}
              </div>

              <div className="text-center">
                <p className="text-xs font-medium text-foreground">{agent.name}</p>
                <p className="text-[10px] text-muted-foreground">{roleLabel[agent.role] || agent.role}</p>
              </div>

              {isSpeaking && (
                <div className="flex items-end gap-0.5 h-3">
                  {[0, 1, 2, 3].map((j) => (
                    <div
                      key={j}
                      className="w-0.5 bg-primary rounded-full"
                      style={{
                        height: `${4 + Math.random() * 8}px`,
                        animation: `gentle-pulse ${0.5 + j * 0.15}s ease-in-out infinite alternate`,
                      }}
                    />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Document tray */}
      <div className="border-t border-border bg-card">
        <div className="flex items-center gap-2 px-5 py-2">
          <FileText className="w-3.5 h-3.5 text-muted-foreground" />
          <span className="text-xs text-muted-foreground font-medium">Documents</span>
          <span className="text-xs text-muted-foreground ml-auto">{documents.length}</span>
        </div>

        <div className="flex items-center gap-2 px-5 pb-3 overflow-x-auto">
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".pdf,.doc,.docx,.txt,.md"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onUpload(file);
            }}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="shrink-0 w-24 h-16 rounded-xl border-2 border-dashed border-border hover:border-primary/40 hover:bg-primary/5 flex flex-col items-center justify-center gap-1 transition-all"
          >
            <Upload className="w-4 h-4 text-muted-foreground" />
            <span className="text-[10px] text-muted-foreground">Upload</span>
          </button>

          {documents.map((doc) => (
            <div
              key={doc.id}
              className="shrink-0 w-36 h-16 rounded-xl border border-border bg-secondary/50 hover:bg-secondary p-2.5 flex flex-col justify-between transition-all cursor-pointer"
            >
              <div className="flex items-center gap-1.5">
                {statusIcons[doc.status]}
                <span className="text-[11px] font-medium text-foreground truncate flex-1">{doc.name}</span>
              </div>
              {doc.summary ? (
                <p className="text-[10px] text-muted-foreground line-clamp-1">{doc.summary}</p>
              ) : (
                <p className="text-[10px] text-muted-foreground capitalize">{doc.status}…</p>
              )}
            </div>
          ))}

          {documents.length === 0 && (
            <p className="text-xs text-muted-foreground py-2">No documents yet</p>
          )}
        </div>
      </div>
    </div>
  );
}
