# SPEC-007: Dashboard UI

**Status:** Draft
**Priority:** P0
**Phase:** 5 (Weeks 10-11), with shell in Phase 1 (Week 2)
**Dependencies:** SPEC-009 (API Contracts), SPEC-008 (Data Model)

---

## 1. Overview

The Quorum Dashboard is a modern web application built with Next.js 16, shadcn/ui, and Tailwind CSS v4. It serves as the command center for monitoring agents, reviewing papers, managing publications, and tracking token costs.

## 2. Technology Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| Next.js | 16.x | Framework (App Router, Server Components) |
| React | 19.x | UI library |
| TypeScript | 5.x | Type safety |
| Tailwind CSS | 4.x | Styling |
| shadcn/ui | Latest | Component primitives |
| Zustand | 5.x | Client state management |
| React Hook Form | 7.x | Form handling |
| Zod | 3.x | Schema validation |
| Recharts | 2.x | Charts and graphs |
| PDF.js | Latest | PDF document viewer |
| next-themes | Latest | Dark mode |

## 3. Page Structure

```
/                       -> Redirect to /dashboard
/login                  -> Authentication page
/dashboard              -> Home dashboard
/agents                 -> Agents panel (list all agents)
/agents/:id             -> Individual agent detail
/files                  -> Files explorer
/review                 -> Review center
/review/:paperId        -> Review a specific paper
/tokens                 -> Token usage dashboard
/deadlines              -> Submission deadline tracker
/settings               -> Settings panel
```

## 4. Layout

### 4.1 App Shell

```
+---------------------------------------------------+
|  Logo    Quorum           [Bell] [Theme] [User]|
+--------+------------------------------------------+
|        |                                          |
| [Home] |        Main Content Area                 |
| [Agent]|                                          |
| [Files]|                                          |
| [Revie]|                                          |
| [Token]|                                          |
| [Deadl]|                                          |
| [Setti]|                                          |
|        |                                          |
|        |                                          |
+--------+------------------------------------------+
```

- **Sidebar**: Collapsible navigation with icons and labels
- **Header**: Logo, breadcrumbs, notification bell (badge count), theme toggle, user avatar
- **Main area**: Full-width content for the active page

### 4.2 Responsive Behavior

| Breakpoint | Sidebar | Layout |
|-----------|---------|--------|
| Desktop (>= 1280px) | Expanded with labels | Full layout |
| Tablet (768-1279px) | Collapsed (icons only) | Full layout |
| Mobile (< 768px) | Hidden (hamburger menu) | Single column |

## 5. Page Wireframes

### 5.1 Home Dashboard (`/dashboard`)

```
+------------------------------------------+
| Welcome back, Harish            April 10  |
+------------------------------------------+
|                                          |
| [Agent Status Cards - 3 columns]        |
| +----------+ +----------+ +----------+  |
| | IEEE     | | SmallPap | | Blog     |  |
| | Active   | | Idle     | | Active   |  |
| | Task: .. | | Last: .. | | Task: .. |  |
| +----------+ +----------+ +----------+  |
|                                          |
| [Recent Papers]              [Budget]    |
| +----------------------+ +------------+  |
| | Title    | Type |Stat| | $7.20/$10  |  |
| | Paper A  | IEEE |Rev | | ████░░ 72% |  |
| | Paper B  | Blog |App | |            |  |
| | Paper C  | Short|Pen | | Monthly:   |  |
| | Paper D  | IEEE |Rev | | $189/$300  |  |
| +----------------------+ +------------+  |
|                                          |
| [Recent Activity Feed]                   |
| - IEEE Agent completed "ZK-Proofs..."    |
| - Review Agent rejected "Federated..."   |
| - Blog Part 2 published to dev.to       |
+------------------------------------------+
```

Components:
- `AgentStatusCard`: Shows agent name, status (active/idle/error), current task, last completion time
- `RecentPapersTable`: Sortable table with title, type, status, date
- `BudgetGauge`: Circular progress showing daily and monthly budget consumption
- `ActivityFeed`: Chronological list of recent events

### 5.2 Agents Panel (`/agents`)

```
+------------------------------------------+
| Agents                    [Refresh]       |
+------------------------------------------+
| +----------+ +----------+ +----------+   |
| | Research | | IEEE     | | Small    |   |
| | Orchestr | | Agent    | | Paper    |   |
| |          | |          | |          |   |
| | Status:  | | Status:  | | Status:  |   |
| | Active   | | Working  | | Idle     |   |
| | Tokens:  | | Tokens:  | | Tokens:  |   |
| | 45.2K    | | 230.1K   | | 12.8K    |   |
| | [View]   | | [View]   | | [View]   |   |
| +----------+ +----------+ +----------+   |
| +----------+ +----------+ +----------+   |
| | Blog     | | Rev:IEEE | | Rev:Blog |   |
| | Agent    | | Agent    | | Agent    |   |
| | ...      | | ...      | | ...      |   |
| +----------+ +----------+ +----------+   |
+------------------------------------------+
```

### 5.3 Agent Detail (`/agents/:id`)

```
+------------------------------------------+
| < Back    IEEE Research Agent    [Assign] |
+------------------------------------------+
| [Files] [Current Tasks] [History] [Stats]|
+------------------------------------------+
|                                          |
| FILES TAB:                               |
| +--------------------------------------+ |
| | Name          | Date    | Status     | |
| | zk-v2v.pdf    | Apr 10  | Approved   | |
| | fed-learn.pdf | Apr 09  | In Review  | |
| | consensus.pdf | Apr 08  | Rejected   | |
| +--------------------------------------+ |
|                                          |
| CURRENT TASKS TAB:                       |
| +--------------------------------------+ |
| | Task              | Phase  | Model  | |
| | ZK-Proofs Paper   | Ideate | Opus   | |
| | Sub-agent 1/5     | Scout  | Haiku  | |
| | Sub-agent 2/5     | Write  | Sonnet | |
| +--------------------------------------+ |
|                                          |
| MANUAL TASK ASSIGNMENT:                  |
| [Topic input field                    ]  |
| [Content type dropdown: IEEE/Short/Blog] |
| [Assign Task]                            |
+------------------------------------------+
```

### 5.4 Review Center (`/review/:paperId`)

This is the most critical UI component -- a 3-panel layout:

```
+------------------------------------------+
| Review Center             [All Reviews]  |
+------------------------------------------+
| List    | Document Viewer  | Comments    |
| --------|------------------|-------------|
| [Filte] |                  | Add Note:   |
|         |  +------------+  | [Text area] |
| IEEE    |  |            |  | [Add]       |
| > zk-v  |  |   PDF.js   |  |-------------|
| > fed-l  |  |  Document  |  | Note 1:     |
|         |  |   Viewer   |  | "Section 3  |
| Short   |  |            |  |  needs more |
| > cons  |  |            |  |  detail"    |
|         |  |            |  |             |
| Blog    |  +------------+  | Note 2:     |
| > auto  |                  | "Good intro |
|         |  Page 1 of 8     |  but weak   |
|         |  [<] [>]         |  conclusion" |
|         |                  |             |
+---------+--[Send Feedback]-+-[Approve]---+
```

Components:
- **Left Panel** (`ReviewFileList`):
  - Grouped by content type (IEEE, Short, Blog)
  - Each paper shows title, date, revision count
  - Filter by status: pending, in-review, revised
  - Click to load in center panel

- **Center Panel** (`DocumentViewer`):
  - For LaTeX/PDF: PDF.js embedded viewer with page navigation, zoom
  - For Blog Markdown: Rendered Markdown preview
  - Page indicators and navigation controls

- **Right Panel** (`CommentPanel`):
  - "Add Note" form: textarea + submit button
  - List of existing comments (reverse chronological)
  - Each comment shows text, timestamp, author (user or agent)
  - Comments from review agents shown with agent badge

- **Action Bar** (bottom):
  - "Send Feedback" button: packages all comments -> sends to backend -> triggers agent rework
  - "Approve" button: marks paper as approved -> moves to approved files list

### 5.5 Token Usage (`/tokens`)

```
+------------------------------------------+
| Token Usage                              |
+------------------------------------------+
| Daily Budget         Monthly Budget      |
| +----------------+ +------------------+  |
| |   ████░░░      | |   ████████░░     |  |
| |   $7.20/$10    | |   $189.50/$300   |  |
| +----------------+ +------------------+  |
|                                          |
| [Daily Trend Line Chart]                 |
| $15 |          *                         |
| $10 |    *   *   *  *                    |
|  $5 |  *               *  *             |
|  $0 +--+--+--+--+--+--+--+-->           |
|      Apr 3  5  6  7  8  9  10           |
|                                          |
| [Cost by Agent]       [Cost by Model]    |
| +--------------+   +----------------+   |
| | IEEE    45%  |   | Opus    35%    |   |
| | Orchestr 20%|   | Sonnet  45%    |   |
| | Blog    15% |   | Haiku   20%    |   |
| | Reviews 10% |   +----------------+   |
| | Other   10% |                         |
| +--------------+                         |
|                                          |
| [Downgrades Today: 3]                   |
| [30-day Forecast: $245]                 |
+------------------------------------------+
```

### 5.6 Settings (`/settings`)

```
+------------------------------------------+
| Settings                                 |
+------------------------------------------+
| [API Keys] [Notifications] [Topics]      |
| [Budget] [Publishing]                    |
+------------------------------------------+
|                                          |
| API KEYS TAB:                            |
| Anthropic API Key: [••••••••••] [Show]   |
| Status: Connected ✓                      |
|                                          |
| NOTIFICATIONS TAB:                       |
| Telegram Bot Token: [•••••••••] [Show]   |
| Telegram Chat ID:   [123456789]          |
| Test: [Send Test Message]                |
|                                          |
| TOPICS TAB:                              |
| Niche Topics:                            |
| [x] Blockchain                           |
| [x] Autonomous Vehicles                  |
| [x] AI/ML Systems                        |
| [ ] IoT Security                         |
| [+ Add Topic]                            |
|                                          |
| Custom Keywords:                         |
| [blockchain, V2V, federated, ZK-proofs]  |
|                                          |
| BUDGET TAB:                              |
| Daily Limit: [$10.00]                    |
| Monthly Limit: [$300.00]                 |
| Auto-downgrade: [Toggle ON]             |
| Pause on exhaustion: [Toggle ON]        |
|                                          |
| PUBLISHING TAB:                          |
| dev.to API Key: [•••••••••] [Show]       |
| Default publish mode: [Draft v]          |
|                                          |
| [Save Settings]                          |
+------------------------------------------+
```

### 5.7 Deadline Tracker (`/deadlines`)

```
+------------------------------------------+
| Submission Deadlines          [+ Add]    |
+------------------------------------------+
| Upcoming                                 |
| +--------------------------------------+ |
| | IEEE ICBC 2026                       | |
| | Deadline: July 15, 2026  (96 days)   | |
| | Papers targeting: 2                   | |
| | ██████████░░░░░ 64%                   | |
| +--------------------------------------+ |
| | IEEE IV 2027                          | |
| | Deadline: Jan 15, 2027  (280 days)   | |
| | Papers targeting: 0                   | |
| +--------------------------------------+ |
|                                          |
| Past Deadlines                           |
| +--------------------------------------+ |
| | IEEE Blockchain 2026  - Submitted: 1 | |
| +--------------------------------------+ |
+------------------------------------------+
```

## 6. Component Library

### shadcn/ui Components Used

| Component | Usage |
|-----------|-------|
| `Button` | All action buttons |
| `Card` | Agent cards, stat cards, paper cards |
| `Table` | File lists, task lists, usage data |
| `Tabs` | Agent detail tabs, settings tabs, review type tabs |
| `Dialog` | Confirmation dialogs, manual task assignment |
| `Input` / `Textarea` | Forms, comment input, search |
| `Select` | Dropdowns (content type, filters) |
| `Badge` | Status badges (active, idle, approved, rejected) |
| `Toggle` | Dark mode, boolean settings |
| `Separator` | Section dividers |
| `Skeleton` | Loading states |
| `Toast` | Success/error notifications |
| `ScrollArea` | Scrollable panels in review center |
| `ResizablePanelGroup` | 3-panel review center layout |
| `Sheet` | Mobile sidebar |
| `Command` | Search/command palette |

### Custom Components

| Component | Description |
|-----------|-------------|
| `AgentStatusCard` | Card showing agent status, current task, token count |
| `BudgetGauge` | Circular progress for budget visualization |
| `DocumentViewer` | PDF.js wrapper with page navigation |
| `MarkdownPreview` | Rendered Markdown for blog preview |
| `CommentPanel` | Review comments list with add form |
| `ReviewFileList` | Grouped file list for review center |
| `TokenChart` | Recharts wrapper for token usage visualization |
| `DeadlineCard` | Countdown card for submission deadlines |
| `ActivityFeed` | Chronological event list |

## 7. State Management

### Zustand Stores

```typescript
// stores/agentStore.ts
interface AgentStore {
  agents: Agent[];
  activeAgent: Agent | null;
  fetchAgents: () => Promise<void>;
  setActiveAgent: (id: string) => void;
}

// stores/reviewStore.ts
interface ReviewStore {
  papers: Paper[];
  activePaper: Paper | null;
  comments: Comment[];
  addComment: (text: string) => void;
  submitFeedback: () => Promise<void>;
  approvePaper: () => Promise<void>;
}

// stores/tokenStore.ts
interface TokenStore {
  budget: BudgetConfig;
  dailyUsage: UsageData[];
  agentUsage: Record<string, number>;
  fetchUsage: (range: DateRange) => Promise<void>;
}

// stores/wsStore.ts
interface WebSocketStore {
  connected: boolean;
  events: WSEvent[];
  connect: () => void;
  disconnect: () => void;
}
```

## 8. Real-Time Updates

### WebSocket Integration

```typescript
// hooks/useWebSocket.ts
function useWebSocket() {
  const { addEvent, setConnected } = useWSStore();

  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/ws`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'agent.status':
          updateAgentStatus(data.payload);
          break;
        case 'task.progress':
          updateTaskProgress(data.payload);
          break;
        case 'paper.created':
          addNewPaper(data.payload);
          showToast('New paper generated');
          break;
        case 'review.completed':
          updateReviewStatus(data.payload);
          showToast('Review completed');
          break;
        case 'token.usage':
          updateTokenUsage(data.payload);
          break;
        case 'budget.alert':
          showBudgetAlert(data.payload);
          break;
      }
    };

    return () => ws.close();
  }, []);
}
```

## 9. Authentication Flow

```
/login page
    |
    v
User enters email + password (or first-time setup)
    |
    v
POST /api/v1/auth/login -> returns JWT + refresh token
    |
    v
JWT stored in httpOnly cookie
    |
    v
Next.js middleware validates JWT on every request
    |
    v
If expired: auto-refresh via POST /api/v1/auth/refresh
    |
    v
If refresh fails: redirect to /login
```

## 10. Dark Mode

Implemented via `next-themes`:
- Toggle in header
- System preference detection
- Persisted in localStorage
- All shadcn/ui components auto-adapt via CSS variables
- Charts (Recharts) use theme-aware colors
