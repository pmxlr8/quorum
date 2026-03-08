export type AgentRole = "chairperson" | "analyst" | "advocate" | "critic" | "secretary" | "creative" | "technical" | "financial" | "custom";
export type VoteValue = "yes" | "no" | "abstain";
export type SessionStatus = "idle" | "connecting" | "active" | "error" | "ended";
export type SpeakingState = "idle" | "listening" | "speaking" | "thinking";

export interface Agent {
  id: string;
  name: string;
  role: AgentRole;
  avatar: string;
  speakingState: SpeakingState;
  isHandRaised: boolean;
}

/** Full agent definition from backend (for creation/editing) */
export interface AgentDefinition {
  id: string;
  name: string;
  role: string;
  label: string;
  description: string;
  personality: string;
  speaking_style: string;
  tone: string;
  expertise: string[];
  voice: string;
  avatar_url: string;
  background_theme: string;
  is_builtin: boolean;
}

export interface VoiceOption {
  id: string;
  label: string;
  description: string;
}

export interface TranscriptEntry {
  id: string;
  agentId: string;
  agentName: string;
  role: AgentRole;
  text: string;
  timestamp: number;
}

export interface VoteItem {
  id: string;
  motion: string;
  votes: Record<string, VoteValue>;
  status: "open" | "closed";
}

export interface UploadedDocument {
  id: string;
  name: string;
  status: "uploading" | "processing" | "analyzed" | "error";
  summary?: string;
}

export interface WarRoomState {
  sessionStatus: SessionStatus;
  agents: Agent[];
  transcript: TranscriptEntry[];
  currentVote: VoteItem | null;
  documents: UploadedDocument[];
  isMicActive: boolean;
  isSpeakerActive: boolean;
}
