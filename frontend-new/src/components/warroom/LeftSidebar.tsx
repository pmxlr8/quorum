import { useState } from "react";
import {
  Menu,
  X,
  MessageSquare,
  Users,
  BarChart3,
  Plus,
  Clock,
  ChevronRight,
  Search,
  Brain,
  Swords,
  Shield,
  FileSearch,
  Scale,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Agent } from "@/types/warroom";

interface PastSession {
  id: string;
  title: string;
  date: string;
  agentCount: number;
  status: "completed" | "aborted";
}

interface PredefinedAgent {
  id: string;
  name: string;
  role: string;
  description: string;
  icon: React.ReactNode;
}

const PAST_SESSIONS: PastSession[] = [
  { id: "s1", title: "Q4 Budget Allocation", date: "Mar 6, 2026", agentCount: 4, status: "completed" },
  { id: "s2", title: "Market Entry Strategy", date: "Mar 4, 2026", agentCount: 5, status: "completed" },
  { id: "s3", title: "Crisis Response Drill", date: "Mar 1, 2026", agentCount: 3, status: "aborted" },
  { id: "s4", title: "Product Launch Review", date: "Feb 27, 2026", agentCount: 5, status: "completed" },
];

const PREDEFINED_AGENTS: PredefinedAgent[] = [
  { id: "pa1", name: "Strategist", role: "analyst", description: "Deep market & data analysis", icon: <Brain className="w-4 h-4" /> },
  { id: "pa2", name: "Devil's Advocate", role: "critic", description: "Challenges assumptions", icon: <Swords className="w-4 h-4" /> },
  { id: "pa3", name: "Compliance Officer", role: "advocate", description: "Legal & regulatory review", icon: <Shield className="w-4 h-4" /> },
  { id: "pa4", name: "Researcher", role: "secretary", description: "Document & fact retrieval", icon: <FileSearch className="w-4 h-4" /> },
  { id: "pa5", name: "Mediator", role: "chairperson", description: "Conflict resolution & consensus", icon: <Scale className="w-4 h-4" /> },
];

interface LeftSidebarProps {
  currentAgents: Agent[];
  onAddAgent?: (agent: PredefinedAgent) => void;
}

type Tab = "sessions" | "agents" | "stats";

export function LeftSidebar({ currentAgents, onAddAgent }: LeftSidebarProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("sessions");

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="fixed top-3 left-3 z-50 w-10 h-10 rounded-xl bg-card border border-border flex items-center justify-center hover:bg-accent transition-colors shadow-sm"
      >
        <Menu className="w-5 h-5 text-foreground" />
      </button>

      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-foreground/10 backdrop-blur-sm"
          onClick={() => setIsOpen(false)}
        />
      )}

      <div
        className={`fixed top-0 left-0 z-50 h-full w-80 bg-card border-r border-border flex flex-col transition-transform duration-300 ease-out shadow-xl ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-semibold text-xs">Q</span>
            </div>
            <span className="text-sm font-semibold text-foreground">Quorum</span>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-accent transition-colors"
          >
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border">
          {([
            { key: "sessions" as Tab, icon: MessageSquare, label: "Sessions" },
            { key: "agents" as Tab, icon: Users, label: "Agents" },
            { key: "stats" as Tab, icon: BarChart3, label: "Stats" },
          ]).map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium transition-colors border-b-2 ${
                activeTab === tab.key
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <tab.icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {activeTab === "sessions" && (
            <div className="p-3 space-y-2">
              <Button variant="default" size="sm" className="w-full gap-1.5 mb-3">
                <Plus className="w-3.5 h-3.5" />
                New Session
              </Button>
              {PAST_SESSIONS.map((session) => (
                <button
                  key={session.id}
                  className="w-full text-left p-3 rounded-xl hover:bg-accent transition-all group"
                >
                  <div className="flex items-start justify-between mb-1">
                    <h4 className="text-sm font-medium text-foreground">
                      {session.title}
                    </h4>
                    <ChevronRight className="w-3.5 h-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity mt-0.5" />
                  </div>
                  <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {session.date}
                    </span>
                    <span>{session.agentCount} agents</span>
                    <span className={session.status === "completed" ? "text-success" : "text-destructive"}>
                      {session.status}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}

          {activeTab === "agents" && (
            <div className="p-3 space-y-2">
              <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-secondary mb-3">
                <Search className="w-3.5 h-3.5 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search agents…"
                  className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none"
                />
              </div>

              {PREDEFINED_AGENTS.map((agent) => {
                const isActive = currentAgents.some((a) => a.role === agent.role);
                return (
                  <div
                    key={agent.id}
                    className="flex items-center gap-3 p-3 rounded-xl hover:bg-accent transition-all"
                  >
                    <div className="w-9 h-9 rounded-xl bg-secondary flex items-center justify-center text-muted-foreground">
                      {agent.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-medium text-foreground">{agent.name}</h4>
                      <p className="text-[11px] text-muted-foreground">{agent.description}</p>
                    </div>
                    <Button
                      variant={isActive ? "ghost" : "default"}
                      size="sm"
                      className="h-7 px-2.5 text-xs rounded-lg"
                      disabled={isActive}
                      onClick={() => onAddAgent?.(agent)}
                    >
                      {isActive ? "Active" : "Add"}
                    </Button>
                  </div>
                );
              })}
            </div>
          )}

          {activeTab === "stats" && (
            <div className="p-4 space-y-3">
              {[
                { label: "Sessions", value: "12", sub: "+3 this week" },
                { label: "Decisions", value: "34", sub: "89% consensus" },
                { label: "Agents Used", value: "8", sub: "5 unique roles" },
                { label: "Docs Analyzed", value: "47", sub: "12.4k pages" },
              ].map((stat) => (
                <div key={stat.label} className="flex items-center justify-between p-3 rounded-xl bg-secondary/50">
                  <div>
                    <p className="text-xs text-muted-foreground">{stat.label}</p>
                    <p className="text-lg font-semibold text-foreground">{stat.value}</p>
                  </div>
                  <p className="text-[11px] text-muted-foreground">{stat.sub}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
