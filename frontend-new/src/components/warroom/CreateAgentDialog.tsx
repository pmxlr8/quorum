import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Loader2, Sparkles, Volume2, X, Plus } from "lucide-react";
import type { AgentDefinition, VoiceOption } from "@/types/warroom";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const ROLE_OPTIONS = [
  { id: "chairperson", label: "Chairperson / Moderator" },
  { id: "analyst", label: "Analyst / Strategist" },
  { id: "critic", label: "Critic / Devil's Advocate" },
  { id: "advocate", label: "Compliance / Advocate" },
  { id: "secretary", label: "Secretary / Researcher" },
  { id: "creative", label: "Creative / Visionary" },
  { id: "technical", label: "Technical / Engineer" },
  { id: "financial", label: "Financial / CFO" },
  { id: "custom", label: "Custom Role" },
];

const TONE_OPTIONS = [
  "formal", "casual", "aggressive", "diplomatic", "skeptical",
  "optimistic", "measured", "passionate", "dry", "authoritative",
];

const PERSONALITY_PRESETS = [
  {
    label: "The Visionary",
    personality: "Bold, imaginative, future-focused. You think in moonshots and paradigm shifts. You get excited about disruptive ideas and often reference innovation case studies. You push the team to think bigger.",
    speaking_style: "Enthusiastic and forward-looking. You use phrases like 'Imagine if...' and 'What if we could...'. You speak with infectious energy.",
    tone: "optimistic",
  },
  {
    label: "The Pragmatist",
    personality: "Grounded, practical, results-oriented. You cut through hype to focus on what actually works. You value execution over ideation. You've 'seen it all before' and bring hard-won wisdom.",
    speaking_style: "No-nonsense and direct. You ask 'How exactly?' a lot. You ground discussions in reality. You speak efficiently without filler.",
    tone: "measured",
  },
  {
    label: "The Provocateur", 
    personality: "Contrarian, sharp, intellectually aggressive. You exist to challenge consensus and expose blind spots. You play devil's advocate even when you agree, because you believe ideas need stress-testing.",
    speaking_style: "Pointed and challenging. You use 'But...' and 'Actually...' frequently. You ask the questions nobody wants to ask. Your tone has an edge.",
    tone: "aggressive",
  },
  {
    label: "The Diplomat",
    personality: "Empathetic, measured, bridge-builder. You see all sides of an argument and work to find common ground. You de-escalate tension and ensure everyone's voice is heard.",
    speaking_style: "Calm and inclusive. You validate others' points before adding yours. You say 'I hear what you're saying, and...' You speak with warmth.",
    tone: "diplomatic",
  },
];

interface CreateAgentDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated: (agent: AgentDefinition) => void;
}

export function CreateAgentDialog({ open, onClose, onCreated }: CreateAgentDialogProps) {
  const [step, setStep] = useState<"basics" | "personality" | "voice" | "avatar">("basics");
  const [voices, setVoices] = useState<VoiceOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [generatingAvatar, setGeneratingAvatar] = useState(false);

  // Form state
  const [name, setName] = useState("");
  const [role, setRole] = useState("analyst");
  const [label, setLabel] = useState("");
  const [description, setDescription] = useState("");
  const [personality, setPersonality] = useState("");
  const [speakingStyle, setSpeakingStyle] = useState("");
  const [tone, setTone] = useState("measured");
  const [expertise, setExpertise] = useState<string[]>([]);
  const [expertiseInput, setExpertiseInput] = useState("");
  const [voice, setVoice] = useState("Aoede");
  const [avatarUrl, setAvatarUrl] = useState("");

  // Fetch voices on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/voices`)
      .then((r) => r.json())
      .then((d) => setVoices(d.voices || []))
      .catch(() => {});
  }, []);

  const addExpertise = () => {
    if (expertiseInput.trim() && expertise.length < 8) {
      setExpertise([...expertise, expertiseInput.trim()]);
      setExpertiseInput("");
    }
  };

  const removeExpertise = (idx: number) => {
    setExpertise(expertise.filter((_, i) => i !== idx));
  };

  const applyPreset = (preset: typeof PERSONALITY_PRESETS[0]) => {
    setPersonality(preset.personality);
    setSpeakingStyle(preset.speaking_style);
    setTone(preset.tone);
  };

  const generateAvatar = async () => {
    setGeneratingAvatar(true);
    try {
      const res = await fetch(`${API_BASE}/api/generate-avatar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          role: label || role,
          personality: personality.slice(0, 200),
        }),
      });
      const data = await res.json();
      if (data.avatar_url) {
        setAvatarUrl(data.avatar_url);
      }
    } catch (e) {
      console.error("Avatar generation failed:", e);
    }
    setGeneratingAvatar(false);
  };

  const handleCreate = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/agents`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          role,
          label: label || name,
          description,
          personality,
          speaking_style: speakingStyle,
          tone,
          expertise,
          voice,
          avatar_url: avatarUrl,
        }),
      });
      const agent = await res.json();
      onCreated(agent as AgentDefinition);
      resetForm();
      onClose();
    } catch (e) {
      console.error("Failed to create agent:", e);
    }
    setLoading(false);
  };

  const resetForm = () => {
    setStep("basics");
    setName("");
    setRole("analyst");
    setLabel("");
    setDescription("");
    setPersonality("");
    setSpeakingStyle("");
    setTone("measured");
    setExpertise([]);
    setVoice("Aoede");
    setAvatarUrl("");
  };

  const canProceed = () => {
    switch (step) {
      case "basics":
        return name.trim() && description.trim();
      case "personality":
        return personality.trim() && speakingStyle.trim();
      case "voice":
        return !!voice;
      case "avatar":
        return true;
    }
  };

  const steps = ["basics", "personality", "voice", "avatar"] as const;
  const stepIdx = steps.indexOf(step);

  return (
    <Dialog open={open} onOpenChange={(o) => !o && !loading && onClose()}>
      <DialogContent className="sm:max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-lg">Create New Agent</DialogTitle>
          <DialogDescription className="text-sm text-muted-foreground">
            Step {stepIdx + 1} of 4: {step === "basics" ? "Identity" : step === "personality" ? "Personality" : step === "voice" ? "Voice" : "Avatar"}
          </DialogDescription>
        </DialogHeader>

        {/* Progress bar */}
        <div className="flex gap-1 mb-2">
          {steps.map((s, i) => (
            <div
              key={s}
              className={`h-1 flex-1 rounded-full transition-colors ${
                i <= stepIdx ? "bg-primary" : "bg-muted"
              }`}
            />
          ))}
        </div>

        {/* Step 1: Basics */}
        {step === "basics" && (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Agent Name *</Label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Luna, Falcon, Atlas..."
                maxLength={30}
              />
            </div>

            <div className="space-y-2">
              <Label>Role</Label>
              <Select value={role} onValueChange={setRole}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROLE_OPTIONS.map((r) => (
                    <SelectItem key={r.id} value={r.id}>
                      {r.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Title / Label</Label>
              <Input
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                placeholder="e.g. Chief Strategy Officer, Risk Analyst..."
              />
            </div>

            <div className="space-y-2">
              <Label>Description *</Label>
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="One-line description of this agent's purpose..."
                className="h-16 resize-none"
              />
            </div>

            <div className="space-y-2">
              <Label>Areas of Expertise</Label>
              <div className="flex gap-2">
                <Input
                  value={expertiseInput}
                  onChange={(e) => setExpertiseInput(e.target.value)}
                  placeholder="Add expertise..."
                  onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addExpertise())}
                  className="flex-1"
                />
                <Button variant="outline" size="sm" onClick={addExpertise}>
                  <Plus className="w-4 h-4" />
                </Button>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {expertise.map((e, i) => (
                  <Badge key={i} variant="secondary" className="gap-1 text-xs">
                    {e}
                    <X className="w-3 h-3 cursor-pointer" onClick={() => removeExpertise(i)} />
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Personality */}
        {step === "personality" && (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label className="text-xs font-medium">Quick Presets</Label>
              <div className="grid grid-cols-2 gap-2">
                {PERSONALITY_PRESETS.map((preset) => (
                  <button
                    key={preset.label}
                    onClick={() => applyPreset(preset)}
                    className="p-2.5 rounded-xl border border-input hover:border-primary/30 hover:bg-primary/5 text-left transition-all"
                  >
                    <p className="text-xs font-medium text-foreground">{preset.label}</p>
                    <p className="text-[10px] text-muted-foreground mt-0.5 line-clamp-2">
                      {preset.personality.slice(0, 80)}...
                    </p>
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <Label>Personality *</Label>
              <Textarea
                value={personality}
                onChange={(e) => setPersonality(e.target.value)}
                placeholder="Describe this agent's personality in detail. What makes them unique? How do they think? What are their quirks?"
                className="h-28 resize-none"
              />
            </div>

            <div className="space-y-2">
              <Label>Speaking Style *</Label>
              <Textarea
                value={speakingStyle}
                onChange={(e) => setSpeakingStyle(e.target.value)}
                placeholder="How does this agent talk? What phrases do they use? Are they formal or casual? Fast or deliberate?"
                className="h-24 resize-none"
              />
            </div>

            <div className="space-y-2">
              <Label>Tone</Label>
              <div className="flex flex-wrap gap-1.5">
                {TONE_OPTIONS.map((t) => (
                  <button
                    key={t}
                    onClick={() => setTone(t)}
                    className={`px-3 py-1.5 rounded-full text-xs transition-all ${
                      tone === t
                        ? "bg-primary text-primary-foreground"
                        : "bg-secondary text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Voice */}
        {step === "voice" && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Each agent gets a unique voice in the live discussion. Choose one that matches their personality.
            </p>
            <div className="grid grid-cols-2 gap-2">
              {voices.map((v) => (
                <button
                  key={v.id}
                  onClick={() => setVoice(v.id)}
                  className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${
                    voice === v.id
                      ? "border-primary bg-primary/5"
                      : "border-input hover:border-primary/30"
                  }`}
                >
                  <div
                    className={`w-9 h-9 rounded-lg flex items-center justify-center ${
                      voice === v.id
                        ? "bg-primary/10 text-primary"
                        : "bg-secondary text-muted-foreground"
                    }`}
                  >
                    <Volume2 className="w-4 h-4" />
                  </div>
                  <div className="text-left">
                    <p className="text-sm font-medium">{v.label}</p>
                    <p className="text-[10px] text-muted-foreground">{v.description}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 4: Avatar */}
        {step === "avatar" && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Generate an AI avatar for your agent, or skip to use the default.
            </p>
            <div className="flex flex-col items-center gap-4">
              {avatarUrl ? (
                <div className="relative">
                  <img
                    src={avatarUrl}
                    alt={`${name} avatar`}
                    className="w-32 h-32 rounded-2xl object-cover border-2 border-primary/20"
                  />
                  <button
                    onClick={() => setAvatarUrl("")}
                    className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-destructive text-destructive-foreground flex items-center justify-center"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ) : (
                <div className="w-32 h-32 rounded-2xl bg-secondary flex items-center justify-center text-muted-foreground">
                  <span className="text-3xl font-bold">{name ? name[0].toUpperCase() : "?"}</span>
                </div>
              )}

              <Button
                variant="outline"
                onClick={generateAvatar}
                disabled={generatingAvatar || !name}
                className="gap-2"
              >
                {generatingAvatar ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4" />
                )}
                {generatingAvatar ? "Generating..." : "Generate AI Avatar"}
              </Button>
              <p className="text-[10px] text-muted-foreground text-center">
                Uses Google Imagen to create a unique avatar based on the agent's name and personality.
              </p>
            </div>

            {/* Summary */}
            <div className="mt-4 p-3 rounded-xl bg-secondary/50 space-y-1.5">
              <p className="text-xs font-medium text-foreground">Agent Summary</p>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
                <span className="text-muted-foreground">Name</span>
                <span className="text-foreground font-medium">{name || "—"}</span>
                <span className="text-muted-foreground">Role</span>
                <span className="text-foreground">{label || role}</span>
                <span className="text-muted-foreground">Voice</span>
                <span className="text-foreground">{voice}</span>
                <span className="text-muted-foreground">Tone</span>
                <span className="text-foreground">{tone}</span>
                <span className="text-muted-foreground">Expertise</span>
                <span className="text-foreground">{expertise.join(", ") || "—"}</span>
              </div>
            </div>
          </div>
        )}

        {/* Navigation */}
        <div className="flex gap-2 mt-4">
          {stepIdx > 0 ? (
            <Button variant="ghost" onClick={() => setStep(steps[stepIdx - 1])} className="flex-1">
              Back
            </Button>
          ) : (
            <Button variant="ghost" onClick={onClose} className="flex-1">
              Cancel
            </Button>
          )}

          {stepIdx < steps.length - 1 ? (
            <Button
              onClick={() => setStep(steps[stepIdx + 1])}
              disabled={!canProceed()}
              className="flex-1"
            >
              Next
            </Button>
          ) : (
            <Button onClick={handleCreate} disabled={loading || !name.trim()} className="flex-1 gap-2">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
              Create Agent
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
