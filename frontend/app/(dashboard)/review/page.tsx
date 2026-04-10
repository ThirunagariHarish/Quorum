"use client";

import { useEffect } from "react";
import { useReviewStore } from "@/stores/review-store";
import { ReviewFileList } from "@/components/review/review-file-list";
import { DocumentViewer } from "@/components/review/document-viewer";
import { CommentPanel } from "@/components/review/comment-panel";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import type { Paper } from "@/lib/api";

export default function ReviewPage() {
  const {
    papers,
    activePaper,
    comments,
    loading,
    fetchPendingPapers,
    setActivePaper,
    addComment,
    submitFeedback,
    approvePaper,
  } = useReviewStore();

  useEffect(() => {
    fetchPendingPapers();
  }, [fetchPendingPapers]);

  const handleSelect = (paper: Paper) => {
    const reviewId = undefined; // Will be fetched from paper detail in real usage
    setActivePaper(paper, reviewId);
  };

  const handleSubmitFeedback = async () => {
    try {
      const res = await submitFeedback();
      toast.success(res.message);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to submit feedback");
    }
  };

  const handleApprove = async () => {
    try {
      const res = await approvePaper();
      toast.success(res.message);
      fetchPendingPapers();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to approve paper");
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-[240px_1fr_300px] gap-4 h-[calc(100vh-12rem)]">
          <Skeleton className="h-full" />
          <Skeleton className="h-full" />
          <Skeleton className="h-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Review Center</h2>
        <p className="text-muted-foreground">Review and approve generated papers</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[256px_1fr_320px] gap-0 h-[calc(100vh-12rem)] border rounded-lg overflow-hidden">
        {/* Left panel: file list */}
        <div className="border-r bg-card hidden lg:block">
          <ReviewFileList
            papers={papers}
            activePaperId={activePaper?.id || null}
            onSelect={handleSelect}
          />
        </div>

        {/* Center panel: document viewer */}
        <div className="bg-muted/30">
          <DocumentViewer
            paperId={activePaper?.id || null}
            paperType={activePaper?.paper_type}
          />
        </div>

        {/* Right panel: comments */}
        <div className="border-l bg-card hidden lg:flex lg:flex-col">
          <CommentPanel
            comments={comments}
            onAddComment={addComment}
            onSubmitFeedback={handleSubmitFeedback}
            onApprove={handleApprove}
            disabled={!activePaper}
          />
        </div>
      </div>
    </div>
  );
}
