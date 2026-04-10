import { create } from "zustand";
import api, { type Paper, type Comment } from "@/lib/api";

interface ReviewState {
  papers: Paper[];
  activePaper: Paper | null;
  activeReviewId: string | null;
  comments: Comment[];
  loading: boolean;
  fetchPendingPapers: () => Promise<void>;
  setActivePaper: (paper: Paper | null, reviewId?: string) => void;
  fetchComments: (reviewId: string) => Promise<void>;
  addComment: (content: string, severity?: string) => Promise<void>;
  submitFeedback: () => Promise<{ task_id: string; message: string }>;
  approvePaper: () => Promise<{ message: string }>;
}

export const useReviewStore = create<ReviewState>((set, get) => ({
  papers: [],
  activePaper: null,
  activeReviewId: null,
  comments: [],
  loading: false,

  fetchPendingPapers: async () => {
    set({ loading: true });
    try {
      const res = await api.getPapers({ status: "in_review" });
      set({ papers: res.items, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  setActivePaper: (paper, reviewId) => {
    set({ activePaper: paper, activeReviewId: reviewId ?? null, comments: [] });
    if (reviewId) get().fetchComments(reviewId);
  },

  fetchComments: async (reviewId) => {
    try {
      const res = await api.getReviewComments(reviewId);
      set({ comments: Array.isArray(res) ? res : res.items ?? [] });
    } catch {
      /* empty */
    }
  },

  addComment: async (content, severity = "minor") => {
    const reviewId = get().activeReviewId;
    if (!reviewId) return;
    const comment = await api.addComment(reviewId, { content, severity });
    set({ comments: [...get().comments, comment] });
  },

  submitFeedback: async () => {
    const reviewId = get().activeReviewId;
    if (!reviewId) throw new Error("No active review");
    return api.submitFeedback(reviewId);
  },

  approvePaper: async () => {
    const reviewId = get().activeReviewId;
    if (!reviewId) throw new Error("No active review");
    return api.approvePaper(reviewId);
  },
}));
