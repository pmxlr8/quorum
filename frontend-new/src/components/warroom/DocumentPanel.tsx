import { useRef } from "react";
import { Upload, FileText, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { UploadedDocument } from "@/types/warroom";

const statusIcons = {
  uploading: <Loader2 className="w-3.5 h-3.5 animate-spin text-accent" />,
  processing: <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />,
  analyzed: <CheckCircle className="w-3.5 h-3.5 text-primary" />,
  error: <AlertCircle className="w-3.5 h-3.5 text-destructive" />,
};

interface DocumentPanelProps {
  documents: UploadedDocument[];
  onUpload: (file: File) => void;
}

export function DocumentPanel({ documents, onUpload }: DocumentPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-2.5 border-b border-border flex items-center gap-2">
        <FileText className="w-3.5 h-3.5 text-muted-foreground" />
        <h3 className="text-xs font-semibold uppercase tracking-widest font-mono text-muted-foreground">
          Documents
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {documents.length === 0 && (
          <p className="text-xs text-muted-foreground text-center py-4 font-mono">No documents uploaded</p>
        )}
        {documents.map((doc) => (
          <div key={doc.id} className="flex items-start gap-2 p-2.5 rounded-md bg-secondary/50 border border-border">
            {statusIcons[doc.status]}
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-foreground truncate">{doc.name}</p>
              {doc.summary && (
                <p className="text-[10px] text-muted-foreground mt-1 line-clamp-2">{doc.summary}</p>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="p-3 border-t border-border">
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept=".pdf,.doc,.docx,.txt,.md"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onUpload(file);
          }}
        />
        <Button
          variant="outline"
          size="sm"
          className="w-full gap-1.5 text-xs font-mono"
          onClick={() => inputRef.current?.click()}
        >
          <Upload className="w-3.5 h-3.5" />
          UPLOAD DOCUMENT
        </Button>
      </div>
    </div>
  );
}
