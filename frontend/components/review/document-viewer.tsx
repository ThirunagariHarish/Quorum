"use client";

import { useEffect, useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import api from "@/lib/api";
import { FileText } from "lucide-react";

interface DocumentViewerProps {
  paperId: string | null;
  paperType?: string;
}

export function DocumentViewer({ paperId, paperType }: DocumentViewerProps) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [contentType, setContentType] = useState<string>("");

  useEffect(() => {
    if (!paperId) {
      setPreviewUrl(null);
      return;
    }

    setLoading(true);
    api
      .downloadPaper(paperId)
      .then((res) => {
        setPreviewUrl(res.download_url);
        setContentType(
          paperType === "blog" ? "text/markdown" : "application/pdf"
        );
      })
      .catch(() => setPreviewUrl(null))
      .finally(() => setLoading(false));
  }, [paperId, paperType]);

  if (!paperId) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
        <FileText className="h-12 w-12 mb-3" />
        <p className="text-sm">Select a paper to preview</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-4 space-y-4">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-[60vh] w-full" />
      </div>
    );
  }

  if (!previewUrl) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
        <p className="text-sm">Preview not available</p>
      </div>
    );
  }

  if (contentType === "application/pdf") {
    return (
      <iframe
        src={previewUrl}
        className="w-full h-full border-0"
        title="Document Preview"
      />
    );
  }

  return (
    <iframe
      src={previewUrl}
      className="w-full h-full border-0"
      title="Document Preview"
    />
  );
}
