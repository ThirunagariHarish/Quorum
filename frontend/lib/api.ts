const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = `${BASE_URL}/api/v1`;

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    const res = await fetch(`${API}${path}`, { ...options, headers });

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      const detail = error.detail;
      const message =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((e: { msg?: string }) => e.msg).filter(Boolean).join(" ") ||
              res.statusText
            : res.statusText;
      throw new ApiError(res.status, message, error.code);
    }

    if (res.status === 204) return undefined as T;
    return res.json();
  }

  // ── Auth ──────────────────────────────────────────────────────────

  login(email: string, password: string) {
    return this.request<{
      access_token: string;
      refresh_token: string;
      token_type: string;
      expires_in: number;
    }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  }

  refreshToken(refreshToken: string) {
    return this.request<{ access_token: string; expires_in: number }>(
      "/auth/refresh",
      { method: "POST", body: JSON.stringify({ refresh_token: refreshToken }) }
    );
  }

  getMe() {
    return this.request<{
      id: string;
      email: string;
      display_name: string;
      created_at: string;
    }>("/auth/me");
  }

  setup(email: string, password: string, displayName: string) {
    return this.request<{ access_token: string; refresh_token: string }>(
      "/auth/setup",
      {
        method: "POST",
        body: JSON.stringify({ email, password, display_name: displayName }),
      }
    );
  }

  // ── Papers ────────────────────────────────────────────────────────

  getPapers(params?: Record<string, string>) {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.request<PaginatedResponse<Paper>>(`/papers${qs}`);
  }

  getPaper(id: string) {
    return this.request<PaperDetail>(`/papers/${id}`);
  }

  downloadPaper(id: string, format = "pdf", version?: number) {
    const params = new URLSearchParams({ format });
    if (version) params.set("version", String(version));
    return this.request<{ download_url: string; filename: string; expires_in: number }>(
      `/papers/${id}/download?${params}`
    );
  }

  deletePaper(id: string) {
    return this.request<void>(`/papers/${id}`, { method: "DELETE" });
  }

  // ── Agents ────────────────────────────────────────────────────────

  getAgents() {
    return this.request<{ items: Agent[] }>("/agents");
  }

  getAgent(id: string) {
    return this.request<Agent>(`/agents/${id}`);
  }

  getAgentTasks(id: string, params?: Record<string, string>) {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.request<PaginatedResponse<AgentTask>>(`/agents/${id}/tasks${qs}`);
  }

  createAgentTask(
    agentId: string,
    data: { topic: string; content_type: string; target_venue?: string; priority?: number }
  ) {
    return this.request<AgentTask>(`/agents/${agentId}/tasks`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // ── Tasks ─────────────────────────────────────────────────────────

  getTasks(params?: Record<string, string>) {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.request<PaginatedResponse<AgentTask>>(`/tasks${qs}`);
  }

  getTask(id: string) {
    return this.request<AgentTask>(`/tasks/${id}`);
  }

  updateTask(id: string, data: Record<string, unknown>) {
    return this.request<AgentTask>(`/tasks/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  // ── Reviews ───────────────────────────────────────────────────────

  getReviews(params?: Record<string, string>) {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.request<PaginatedResponse<Review>>(`/reviews${qs}`);
  }

  createReview(data: {
    paper_id: string;
    verdict: string;
    summary: string;
    overall_quality: number;
  }) {
    return this.request<Review>("/reviews", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  getReview(id: string) {
    return this.request<Review>(`/reviews/${id}`);
  }

  getReviewComments(reviewId: string) {
    return this.request<{ items: Comment[] }>(`/reviews/${reviewId}/comments`);
  }

  addComment(
    reviewId: string,
    data: { content: string; severity?: string; category?: string; location?: string }
  ) {
    return this.request<Comment>(`/reviews/${reviewId}/comments`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  submitFeedback(reviewId: string) {
    return this.request<{ task_id: string; message: string; revision_number: number }>(
      `/reviews/${reviewId}/submit-feedback`,
      { method: "POST" }
    );
  }

  approvePaper(reviewId: string) {
    return this.request<{ paper_id: string; status: string; message: string }>(
      `/reviews/${reviewId}/approve`,
      { method: "POST" }
    );
  }

  // ── Token Usage ───────────────────────────────────────────────────

  getTokenUsage(params?: Record<string, string>) {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.request<TokenUsageResponse>(`/tokens/usage${qs}`);
  }

  getBudget() {
    return this.request<BudgetConfig>("/tokens/budget");
  }

  updateBudget(data: Partial<BudgetConfig>) {
    return this.request<BudgetConfig>("/tokens/budget", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  getForecast() {
    return this.request<{
      forecast_30d_usd: number;
      daily_average_7d: number;
      trend: string;
      projected_monthly: number;
    }>("/tokens/forecast");
  }

  // ── Settings ──────────────────────────────────────────────────────

  getSettings() {
    return this.request<{ settings: Record<string, unknown> }>("/settings").then(
      (r) => normalizeSettingsPayload(r.settings)
    );
  }

  updateSettings(data: Partial<Settings>) {
    return this.request<{ settings: Record<string, unknown> }>("/settings", {
      method: "PUT",
      body: JSON.stringify({ settings: data }),
    }).then((r) => normalizeSettingsPayload(r.settings));
  }

  // ── Deadlines ─────────────────────────────────────────────────────

  getDeadlines(params?: Record<string, string>) {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.request<{ items: Deadline[] }>(`/deadlines${qs}`);
  }

  createDeadline(data: {
    venue_name: string;
    venue_type: string;
    submission_deadline: string;
    venue_url?: string;
    topics?: string[];
    page_limit?: number;
    format_notes?: string;
  }) {
    return this.request<Deadline>("/deadlines", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  deleteDeadline(id: string) {
    return this.request<void>(`/deadlines/${id}`, { method: "DELETE" });
  }

  // ── Publishing ────────────────────────────────────────────────────

  publishToDevto(data: {
    paper_id: string;
    part_number?: number;
    published?: boolean;
    tags?: string[];
  }) {
    return this.request<{
      id: string;
      platform: string;
      platform_article_id: string;
      published_url: string;
      status: string;
    }>("/publish/devto", { method: "POST", body: JSON.stringify(data) });
  }

  getPublishStatus(id: string) {
    return this.request<{ id: string; status: string; published_url?: string }>(
      `/publish/status/${id}`
    );
  }

  // ── Scheduler ─────────────────────────────────────────────────────

  triggerScheduler() {
    return this.request<{ message: string; task_id: string }>("/scheduler/trigger", {
      method: "POST",
    });
  }

  getSchedulerStatus() {
    return this.request<{
      is_running: boolean;
      next_morning_run: string;
      next_evening_run: string;
      last_run: string;
      last_run_status: string;
    }>("/scheduler/status");
  }

  // ── Health ────────────────────────────────────────────────────────

  healthCheck() {
    return this.request<{ status: string }>("/health");
  }
}

// ── Error class ───────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code?: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ── Types ─────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
}

export interface Paper {
  id: string;
  title: string;
  abstract: string;
  paper_type: string;
  status: string;
  current_version: number;
  keywords: string[];
  target_venue: string;
  plagiarism_score: number;
  review_cycles: number;
  agent_name: string;
  created_at: string;
  updated_at: string;
}

export interface PaperDetail extends Paper {
  storage_prefix: string;
  pdf_url: string;
  versions: { version: number; created_at: string; change_summary: string }[];
  reviews: { id: string; verdict: string; quality: number; created_at: string }[];
}

export interface Agent {
  id: string;
  name: string;
  agent_type: string;
  default_model: string;
  status: string;
  current_task: { id: string; topic: string; phase: string } | null;
  total_tokens_used: number;
  total_cost_usd: number;
  last_active_at: string;
}

export interface AgentTask {
  id: string;
  agent_id: string;
  topic: string;
  content_type: string;
  status: string;
  phase?: string;
  model?: string;
  priority?: number;
  created_at: string;
  completed_at?: string;
}

export interface Review {
  id: string;
  paper_id: string;
  verdict: string;
  summary: string;
  overall_quality: number;
  is_human_review: boolean;
  created_at: string;
}

export interface Comment {
  id: string;
  review_id: string;
  content: string;
  severity: string;
  category?: string;
  location?: string;
  user_id?: string;
  agent_id?: string;
  created_at: string;
}

export interface TokenUsageResponse {
  data: {
    date: string;
    total_cost_usd: number;
    total_input_tokens: number;
    total_output_tokens: number;
    api_calls: number;
    downgrades: number;
  }[];
  summary: {
    period_cost: number;
    daily_budget: number;
    daily_remaining: number;
    monthly_cost: number;
    monthly_budget: number;
    monthly_remaining: number;
  };
}

export interface BudgetConfig {
  daily_limit_usd: number;
  monthly_limit_usd: number;
  daily_spent: number;
  monthly_spent: number;
  budget_status: string;
  auto_downgrade_enabled: boolean;
  pause_on_exhaustion: boolean;
}

export interface Settings {
  /** Which provider agents use for LLM calls (stored per user). */
  llm_provider: string;
  anthropic_api_key?: string;
  anthropic_api_key_set: boolean;
  openai_api_key?: string;
  openai_api_key_set: boolean;
  google_api_key?: string;
  google_api_key_set: boolean;
  telegram_bot_token?: string;
  telegram_bot_token_set: boolean;
  telegram_chat_id?: string;
  devto_api_key?: string;
  devto_api_key_set: boolean;
  niche_topics: string[];
  custom_keywords: string[];
  daily_budget_usd: number;
  monthly_budget_usd: number;
  auto_downgrade: boolean;
  default_publish_mode?: string;
  schedule_morning?: string;
  schedule_evening?: string;
}

function normalizeSettingsPayload(raw: Record<string, unknown>): Settings {
  return {
    llm_provider: (raw.llm_provider as string) || "anthropic",
    anthropic_api_key_set: Boolean(raw.anthropic_api_key_set),
    openai_api_key_set: Boolean(raw.openai_api_key_set),
    google_api_key_set: Boolean(raw.google_api_key_set),
    telegram_bot_token_set: Boolean(raw.telegram_bot_token_set),
    devto_api_key_set: Boolean(raw.devto_api_key_set),
    anthropic_api_key: raw.anthropic_api_key as string | undefined,
    telegram_bot_token: raw.telegram_bot_token as string | undefined,
    telegram_chat_id: raw.telegram_chat_id as string | undefined,
    devto_api_key: raw.devto_api_key as string | undefined,
    niche_topics: (raw.niche_topics as string[]) ?? [],
    custom_keywords: (raw.custom_keywords as string[]) ?? [],
    daily_budget_usd: Number(raw.daily_budget_usd ?? 10),
    monthly_budget_usd: Number(raw.monthly_budget_usd ?? 300),
    auto_downgrade: Boolean(raw.auto_downgrade ?? true),
    default_publish_mode: raw.default_publish_mode as string | undefined,
    schedule_morning: raw.schedule_morning as string | undefined,
    schedule_evening: raw.schedule_evening as string | undefined,
  };
}

export interface Deadline {
  id: string;
  venue_name: string;
  venue_type: string;
  submission_deadline: string;
  venue_url?: string;
  topics: string[];
  page_limit?: number;
  format_notes?: string;
  papers_count?: number;
  is_active: boolean;
  created_at: string;
}

export const api = new ApiClient();
export default api;

// ---------------------------------------------------------------------------
// LaTeX editor helpers
// ---------------------------------------------------------------------------

export interface CompileResponse {
  pdf_base64: string;
  errors: string[];
  warnings: string[];
}

export async function compilePaper(
  paperId: string,
  tex: string,
  bib?: string
): Promise<CompileResponse> {
  const body: Record<string, string> = { tex };
  if (bib !== undefined) body.bib = bib;
  const res = await fetch(`/api/v1/papers/${paperId}/compile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? `Compile failed: ${res.status}`);
  }
  return res.json() as Promise<CompileResponse>;
}
