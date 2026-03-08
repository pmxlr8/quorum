import { ThumbsUp, ThumbsDown, MinusCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { VoteItem, VoteValue } from "@/types/warroom";

interface VotePanelProps {
  vote: VoteItem | null;
  onCastVote: (value: VoteValue) => void;
  userVote?: VoteValue;
}

export function VotePanel({ vote, onCastVote, userVote }: VotePanelProps) {
  if (!vote) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-4">
        <p className="text-xs text-muted-foreground font-mono text-center">No active motion</p>
      </div>
    );
  }

  const voteCounts = { yes: 0, no: 0, abstain: 0 };
  Object.values(vote.votes).forEach((v) => voteCounts[v]++);
  const totalVotes = Object.keys(vote.votes).length;

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-2.5 border-b border-border flex items-center gap-2">
        <div className={`w-1.5 h-1.5 rounded-full ${vote.status === "open" ? "bg-accent animate-pulse" : "bg-muted-foreground"}`} />
        <h3 className="text-xs font-semibold uppercase tracking-widest font-mono text-muted-foreground">
          {vote.status === "open" ? "Vote in Progress" : "Vote Closed"}
        </h3>
      </div>

      <div className="flex-1 p-4 space-y-4">
        {/* Motion text */}
        <div className="p-3 rounded-md border border-accent/30 bg-accent/5">
          <p className="text-sm font-medium text-foreground">{vote.motion}</p>
        </div>

        {/* Vote buttons */}
        {vote.status === "open" && (
          <div className="grid grid-cols-3 gap-2">
            <Button
              variant="vote"
              size="sm"
              className={`flex-col gap-1 h-auto py-3 ${userVote === "yes" ? "border-primary bg-primary/10" : ""}`}
              onClick={() => onCastVote("yes")}
            >
              <ThumbsUp className="w-4 h-4 text-primary" />
              <span className="text-[10px] font-mono">YES</span>
            </Button>
            <Button
              variant="vote"
              size="sm"
              className={`flex-col gap-1 h-auto py-3 ${userVote === "no" ? "border-destructive bg-destructive/10" : ""}`}
              onClick={() => onCastVote("no")}
            >
              <ThumbsDown className="w-4 h-4 text-destructive" />
              <span className="text-[10px] font-mono">NO</span>
            </Button>
            <Button
              variant="vote"
              size="sm"
              className={`flex-col gap-1 h-auto py-3 ${userVote === "abstain" ? "border-muted-foreground bg-muted/50" : ""}`}
              onClick={() => onCastVote("abstain")}
            >
              <MinusCircle className="w-4 h-4 text-muted-foreground" />
              <span className="text-[10px] font-mono">ABSTAIN</span>
            </Button>
          </div>
        )}

        {/* Results bar */}
        {totalVotes > 0 && (
          <div className="space-y-1.5">
            <div className="flex gap-0.5 h-2 rounded-full overflow-hidden bg-secondary">
              {voteCounts.yes > 0 && (
                <div className="bg-primary h-full rounded-full" style={{ width: `${(voteCounts.yes / totalVotes) * 100}%` }} />
              )}
              {voteCounts.no > 0 && (
                <div className="bg-destructive h-full rounded-full" style={{ width: `${(voteCounts.no / totalVotes) * 100}%` }} />
              )}
              {voteCounts.abstain > 0 && (
                <div className="bg-muted-foreground/50 h-full rounded-full" style={{ width: `${(voteCounts.abstain / totalVotes) * 100}%` }} />
              )}
            </div>
            <div className="flex justify-between text-[10px] font-mono text-muted-foreground">
              <span className="text-primary">{voteCounts.yes} Yes</span>
              <span className="text-destructive">{voteCounts.no} No</span>
              <span>{voteCounts.abstain} Abstain</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
