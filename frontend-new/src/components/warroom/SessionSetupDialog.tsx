import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Brain, Swords, Shield, FileSearch, Scale, Loader2, Check, Plus, Trash2, Volume2, Sparkles } from "lucide-react";
import type { AgentDefinition } from "@/types/warroom";
import { CreateAgentDialog } from "./CreateAgentDialog";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const ROLE_ICONS: Record<string, React.ReactNode> = {
  analyst: <Brain className="w-4 h-4" />,
  critic: <Swords className="w-4 h-4" />,
  advocate: <Shield className="w-4 h-4" />,
  secretary: <FileSearch className="w-4 h-4" />,
  chairperson: <Scale className="w-4 h-4" />,
  creative: <Sparkles className="w-4 h-4" />,
  technical: <Brain className="w-4 h-4" />,
  financial: <Scale className="w-4 h-4" />,
  custom: <Plus className="w-4 h-4" />,
};

export interface SessionConfig {
  agenda: string;
  selectedAgentIds: string[];
}

interface SessionSetupDialogProps {
  open: boolean;
  onStart: (config: SessionConfig) => void;
  onCancel: () => void;
}

export function SessionSetupDialog({ open, onStart, onCancel }: SessionSetupDialogProps) {
  const [step, setStep] = useState<"setup" | "loading">("setup");
  const [agenda, setAgenda] = useState("");
  const [selectedAgents, setSelectedAgents] = useState<Set<string>>(new Set(["pa1", "pa2", "pa5"]));
  const [agents, setAgents] = useState<AgentDefinition[]>([]);
  const [showCreateAgent, setShowCreateAgent] = useState(false);
  const [loadingAgents, setLoadingAgents] = useState(false);

  // Fetch agents from backend
  useEffect(() => {
    if (open) {
      setLoadingAgents(true);
      fetch(`${API_BASE}/api/agents`)
        .then((r) => r.json())
        .then((d) => setAgents(d.agents || []))
        .catch(() => {})
        .finally(() => setLoadingAgents(false));
    }
  }, [open]);

  const toggleAgent = (id: string) => {
    setSelectedAgents((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleDeleteAgent = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await fetch(`${API_BASE}/api/agents/${id}`, { method: "DELETE" });
      setAgents((prev) => prev.filter((a) => a.id !== id));
      setSelectedAgents((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    } catch (err) {
      console.error("Failed to delete agent:", err);
    }
  };

  const handleAgentCreated = (agent: AgentDefinition) => {
    setAgents((prev) => [...prev, agent]);
    setSelectedAgents((prev) => new Set([...prev, agent.id]));
  };

  const handleStart = () => {
    setStep("loading");
    setTimeout(() => {
      onStart({ agenda, selectedAgentIds: Array.from(selectedAgents) });
      setStep("setup");
      setAgenda("");
    }, 1500);
  };

  return (
    <>
      <Dialog open={open} onOpenChange={(o) => !o && step !== "loading" && onCancel()}>
        <DialogContent className="sm:max-w-lg max-h-[85vh] overflow-y-auto">
          {step === "setup" ? (
            <>
              <DialogHeader>
                <DialogTitle className="text-lg">New Session</DialogTitle>
                <DialogDescription className="text-sm text-muted-foreground">
                  Set your agenda and choose who joins the room. Each agent has a unique voice and personality.
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4 mt-2">
                {/* Agenda */}
                <div className="space-y-2">
                  <label className="text-xs font-medium text-foreground">Agenda</label>
                  <textarea
                    value={agenda}
                    onChange={(e) => setAgenda(e.target.value)}
                    placeholder="What should the board discuss today?"
                    className="w-full h-20 rounded-xl border border-input bg-background px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:ring-2 focus:ring-ring resize-none"
                  />
                </div>

                {/* Agent selection */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-medium text-foreground">
                      Agents ({selectedAgents.size} selected)
                    </label>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 text-xs gap-1"
                      onClick={() => setShowCreateAgent(true)}
                    >
                      <Plus className="w-3 h-3" />
                      Create Agent
                    </Button>
                  </div>

                  {loadingAgents ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                    </div>
                  ) : (
                    <div className="space-y-1.5 max-h-[300px] overflow-y-auto pr-1">
                      {agents.map((agent) => {
                        const selected = selectedAgents.has(agent.id);
                        const icon = ROLE_ICONS[agent.role] || <Brain className="w-4 h-4" />;
                        return (
                          <button
                            key={agent.id}
                            onClick={() => toggleAgent(agent.id)}
                            className={`w-full flex items-center gap-3 p-2.5 rounded-xl text-left transition-all ${
                              selected
                                ? "bg-primary/8 border border-primary/20"
                                : "hover:bg-accent border border-transparent"
                            }`}
                          >
                            {/* Avatar or icon */}
                            {agent.avatar_url ? (
                              <img
                                src={agent.avatar_url}
                                alt={agent.name}
                                className="w-8 h-8 rounded-lg object-cover"
                              />
                            ) : (
                              <div
                                className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                                  selected
                                    ? "bg-primary/10 text-primary"
                                    : "bg-secondary text-muted-foreground"
                                }`}
                              >
                                {icon}
                              </div>
                            )}

                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <p className="text-sm font-medium text-foreground">
                                  {agent.name}
                                </p>
                                <Badge variant="outline" className="text-[9px] h-4 px-1.5">
                                  {agent.voice}
                                </Badge>
                                {!agent.is_builtin && (
                                  <Badge variant="secondary" className="text-[9px] h-4 px-1.5">
                                    Custom
                                  </Badge>
                                )}
                              </div>
                              <p className="text-[11px] text-muted-foreground truncate">
                                {agent.label} — {agent.description}
                              </p>
                            </div>

                            <div className="flex items-center gap-1.5 shrink-0">
                              {!agent.is_builtin && (
                                <button
                                  onClick={(e) => handleDeleteAgent(agent.id, e)}
                                  className="w-6 h-6 rounded-md flex items-center justify-center hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                                >
                                  <Trash2 className="w-3 h-3" />
                                </button>
                              )}
                              {selected && <Check className="w-4 h-4 text-primary" />}
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>

              <div className="flex gap-2 mt-4">
                <Button variant="ghost" onClick={onCancel} className="flex-1">
                  Cancel
                </Button>
                <Button
                  onClick={handleStart}
                  disabled={!agenda.trim() || selectedAgents.size === 0}
                  className="flex-1"
                >
                  Start Session ({selectedAgents.size} agents)
                </Button>
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 gap-4">
              <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center">
                <Loader2 className="w-6 h-6 text-primary animate-spin" />
              </div>
              <div className="text-center space-y-1">
                <p className="text-sm font-medium text-foreground">Setting up your war room</p>
                <p className="text-xs text-muted-foreground">
                  Initializing {selectedAgents.size} agents with unique voices...
                </p>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <CreateAgentDialog
        open={showCreateAgent}
        onClose={() => setShowCreateAgent(false)}
        onCreated={handleAgentCreated}
      />
    </>
  );
}
