"use client";

import { useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import type { Comment } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { Bot, Loader2, MessageSquarePlus, Send, User } from "lucide-react";

interface CommentPanelProps {
  comments: Comment[];
  onAddComment: (content: string) => Promise<void>;
  onSubmitFeedback: () => Promise<void>;
  onApprove: () => Promise<void>;
  disabled?: boolean;
}

export function CommentPanel({
  comments,
  onAddComment,
  onSubmitFeedback,
  onApprove,
  disabled,
}: CommentPanelProps) {
  const [note, setNote] = useState("");
  const [addingNote, setAddingNote] = useState(false);
  const [submittingFeedback, setSubmittingFeedback] = useState(false);
  const [approving, setApproving] = useState(false);

  const handleAddNote = async () => {
    if (!note.trim()) return;
    setAddingNote(true);
    try {
      await onAddComment(note);
      setNote("");
    } finally {
      setAddingNote(false);
    }
  };

  const handleSubmitFeedback = async () => {
    setSubmittingFeedback(true);
    try {
      await onSubmitFeedback();
    } finally {
      setSubmittingFeedback(false);
    }
  };

  const handleApprove = async () => {
    setApproving(true);
    try {
      await onApprove();
    } finally {
      setApproving(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Add Note */}
      <div className="p-3 space-y-2 border-b">
        <div className="flex items-center gap-2">
          <MessageSquarePlus className="h-4 w-4 text-muted-foreground" />
          <h4 className="text-sm font-medium">Add Note</h4>
        </div>
        <Textarea
          placeholder="Write your review comment..."
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={3}
          className="resize-none text-sm"
          disabled={disabled}
        />
        <Button
          size="sm"
          className="w-full"
          disabled={!note.trim() || addingNote || disabled}
          onClick={handleAddNote}
        >
          {addingNote ? (
            <Loader2 className="mr-2 h-3 w-3 animate-spin" />
          ) : (
            <Send className="mr-2 h-3 w-3" />
          )}
          Add
        </Button>
      </div>

      {/* Comments list */}
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-3">
          {comments.length === 0 && (
            <p className="text-xs text-muted-foreground text-center py-6">
              No comments yet
            </p>
          )}
          {comments.map((comment) => (
            <div key={comment.id} className="space-y-1">
              <div className="flex items-center gap-2">
                {comment.agent_id ? (
                  <Bot className="h-3 w-3 text-blue-500" />
                ) : (
                  <User className="h-3 w-3 text-muted-foreground" />
                )}
                <span className="text-xs font-medium">
                  {comment.agent_id ? "Agent" : "You"}
                </span>
                {comment.severity && (
                  <Badge variant="outline" className="text-[10px] px-1 py-0">
                    {comment.severity}
                  </Badge>
                )}
                <span className="text-[10px] text-muted-foreground ml-auto">
                  {formatDate(comment.created_at, {
                    month: "short",
                    day: "numeric",
                    hour: "numeric",
                    minute: "numeric",
                  })}
                </span>
              </div>
              <p className="text-sm text-foreground leading-relaxed pl-5">
                {comment.content}
              </p>
              {comment.location && (
                <p className="text-[10px] text-muted-foreground pl-5">
                  {comment.location}
                </p>
              )}
            </div>
          ))}
        </div>
      </ScrollArea>

      {/* Action buttons */}
      <Separator />
      <div className="p-3 flex gap-2">
        <Button
          variant="outline"
          size="sm"
          className="flex-1"
          disabled={submittingFeedback || disabled}
          onClick={handleSubmitFeedback}
        >
          {submittingFeedback && <Loader2 className="mr-2 h-3 w-3 animate-spin" />}
          Send Feedback
        </Button>
        <Button
          size="sm"
          className="flex-1 bg-green-600 hover:bg-green-700 text-white"
          disabled={approving || disabled}
          onClick={handleApprove}
        >
          {approving && <Loader2 className="mr-2 h-3 w-3 animate-spin" />}
          Approve
        </Button>
      </div>
    </div>
  );
}
