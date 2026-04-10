"use client";

import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Paper } from "@/lib/api";
import { FileText } from "lucide-react";

interface ReviewFileListProps {
  papers: Paper[];
  activePaperId: string | null;
  onSelect: (paper: Paper) => void;
}

export function ReviewFileList({ papers, activePaperId, onSelect }: ReviewFileListProps) {
  const grouped = papers.reduce<Record<string, Paper[]>>((acc, paper) => {
    const type = paper.paper_type;
    if (!acc[type]) acc[type] = [];
    acc[type].push(paper);
    return acc;
  }, {});

  const typeLabels: Record<string, string> = {
    ieee_full: "IEEE Full Papers",
    ieee_short: "IEEE Short Papers",
    workshop: "Workshop Papers",
    poster: "Posters",
    blog: "Blog Posts",
  };

  return (
    <ScrollArea className="h-full">
      <div className="p-3 space-y-4">
        {Object.entries(grouped).map(([type, typePapers]) => (
          <div key={type}>
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 px-2">
              {typeLabels[type] || type}
            </h4>
            <div className="space-y-1">
              {typePapers.map((paper) => (
                <button
                  key={paper.id}
                  onClick={() => onSelect(paper)}
                  className={cn(
                    "w-full flex items-start gap-2 rounded-lg px-2 py-2 text-left text-sm transition-colors",
                    "hover:bg-accent",
                    paper.id === activePaperId && "bg-accent"
                  )}
                >
                  <FileText className="h-4 w-4 mt-0.5 shrink-0 text-muted-foreground" />
                  <div className="min-w-0 flex-1">
                    <p className="font-medium truncate">{paper.title}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <Badge
                        variant="secondary"
                        className="text-[10px] px-1.5 py-0"
                      >
                        v{paper.current_version}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {paper.review_cycles} review{paper.review_cycles !== 1 ? "s" : ""}
                      </span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        ))}
        {papers.length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-8">
            No papers pending review
          </p>
        )}
      </div>
    </ScrollArea>
  );
}
