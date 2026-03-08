import { Target } from "lucide-react";

interface MissionCardProps {
  title: string;
  description: string;
}

export function MissionCard({ title, description }: MissionCardProps) {
  return (
    <div className="p-4 border border-primary/20 rounded-lg bg-primary/5 relative overflow-hidden">
      <div className="absolute top-0 right-0 w-24 h-24 bg-primary/5 rounded-full -translate-y-1/2 translate-x-1/2" />
      <div className="flex items-start gap-3 relative">
        <div className="w-8 h-8 rounded-md bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
          <Target className="w-4 h-4 text-primary" />
        </div>
        <div>
          <h2 className="text-sm font-bold text-foreground font-display">{title}</h2>
          <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{description}</p>
        </div>
      </div>
    </div>
  );
}
