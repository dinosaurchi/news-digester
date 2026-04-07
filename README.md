# SME News Admin

A production-ready admin dashboard for managing AI-powered news intelligence workspaces. Monitor feeds, review scored content, interact with report threads, and track operational runs — all in a clean, operator-grade interface.

## Features

- **Workspace Management** — Create and manage customer reporting environments
- **Business Profiles** — Define intelligence context with products, competitors, and priority themes
- **Feed Management** — Configure RSS feeds, website scrapers, competitor pages, and blog sources
- **Content Inspection** — Review fetched content with multi-factor relevance scoring and source attribution
- **Intelligence Reports** — Chat-style report threads with source inspection, voting, and regeneration
- **Operational Runs** — Monitor intelligence cycle execution with step-by-step timelines and error tracking
- **Feedback & Preferences** — Transparency dashboard showing how user feedback influences report tuning
- **Settings** — Configure scheduling, scoring thresholds, data retention, and email delivery

## Quick Start

### Prerequisites

- Node.js 18+ and npm

### Install & Run

```bash
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) and sign in with any non-empty credentials.

### Production Build

```bash
npm run build
npm run preview
```

## Project Structure

```
src/
├── components/
│   ├── ui/                          # Shared UI primitives
│   │   ├── empty-state.tsx          # Empty state with icon, title, action
│   │   ├── loading-skeleton.tsx     # Skeleton loaders (card, table, stat)
│   │   ├── page-header.tsx          # Consistent page title + description
│   │   ├── score-bar.tsx            # Color-coded score indicator
│   │   ├── sheet.tsx                # Slide-over panel (detail drawers)
│   │   ├── status-badge.tsx         # Color-coded status pill with dot
│   │   ├── step-timeline.tsx        # Vertical step timeline for runs
│   │   ├── toast.tsx                # Toast notification system
│   │   ├── list-editor.tsx          # Add/remove string list editor
│   │   ├── markdown-renderer.tsx    # Styled markdown rendering
│   │   └── typing-indicator.tsx     # Animated typing dots
│   ├── app-layout.tsx               # Main app shell (sidebar + header + outlet)
│   ├── header.tsx                   # Top bar with breadcrumbs and actions
│   ├── sidebar.tsx                  # Collapsible navigation sidebar
│   └── workspace-switcher.tsx       # Dropdown workspace selector
├── hooks/
│   └── use-mobile.ts
├── lib/
│   ├── api.ts                       # API facade (re-exports from mock-api)
│   ├── schemas/                     # Zod validation schemas
│   │   ├── profile.ts
│   │   ├── feeds.ts
│   │   └── settings.ts
│   ├── store.ts                     # Zustand global state (user, workspace, sidebar)
│   ├── types.ts                     # Re-exports all domain types
│   └── utils.ts                     # Formatting utilities (dates, duration, etc.)
├── mock-api/                        # Modular mock API layer
│   ├── index.ts                     # Barrel re-exports
│   ├── helpers.ts                   # delay() and randomBetween() utilities
│   ├── workspaces.ts                # Workspace CRUD
│   ├── profile.ts                   # Business profile get/update
│   ├── feeds.ts                     # Feed source CRUD + toggle + delete
│   ├── content.ts                   # Content list + detail + filters
│   ├── reports.ts                   # Report thread list + summary
│   ├── reportThreads.ts             # Messages, feedback, votes, regeneration
│   ├── runs.ts                      # Run list + detail + trigger
│   ├── feedback.ts                  # Feedback events + summary
│   └── settings.ts                  # Settings get/update
├── pages/                           # Route-level page components
│   ├── LoginPage.tsx                # /login
│   ├── WorkspacesPage.tsx           # /workspaces
│   ├── WorkspaceOverviewPage.tsx    # /workspaces/:id
│   ├── ProfilePage.tsx              # /workspaces/:id/profile
│   ├── FeedsPage.tsx                # /workspaces/:id/feeds
│   ├── ContentPage.tsx              # /workspaces/:id/content
│   ├── ReportsPage.tsx              # /workspaces/:id/reports
│   ├── ReportThreadPage.tsx         # /workspaces/:id/reports/:threadId
│   ├── RunsPage.tsx                 # /workspaces/:id/runs
│   ├── FeedbackPage.tsx             # /workspaces/:id/feedback
│   └── SettingsPage.tsx             # /workspaces/:id/settings
├── router/
│   └── index.tsx                    # React Router configuration
├── types/                           # Domain type definitions
│   ├── workspace.ts
│   ├── profile.ts
│   ├── feeds.ts
│   ├── content.ts
│   ├── reports.ts
│   ├── runs.ts
│   ├── feedback.ts
│   └── settings.ts
├── globals.css                      # Tailwind CSS v4 imports + base styles
└── main.tsx                         # App entry point
```

## Routes

| Path | Page | Description |
|------|------|-------------|
| `/login` | Login | Authentication (any credentials work in demo) |
| `/workspaces` | Workspaces | Workspace grid with search, filters, and creation |
| `/workspaces/:id` | Overview | Dashboard with stat cards, recent runs, and quick actions |
| `/workspaces/:id/profile` | Profile | Business profile editor with form validation |
| `/workspaces/:id/feeds` | Feeds | Feed source table with add/edit/delete in slide-over |
| `/workspaces/:id/content` | Content | Sortable/filterable content table with detail drawer |
| `/workspaces/:id/reports` | Reports | Report thread cards with search and status filters |
| `/workspaces/:id/reports/:threadId` | Thread | Chat-style report with source panel, voting, regeneration |
| `/workspaces/:id/runs` | Runs | Run table with detail drawer showing step timeline |
| `/workspaces/:id/feedback` | Feedback | Transparency dashboard with timeline and preferences |
| `/workspaces/:id/settings` | Settings | Schedule, scoring, retention, and email configuration |

## Mock API

The app uses a fully self-contained mock API in `src/mock-api/`. Each domain module exports:

- **Realistic fixture data** — 2 workspaces with related feeds, content, reports, runs, and feedback
- **Simulated network delays** — 300–800ms random delay per request
- **Full CRUD operations** — create, read, update, delete where applicable
- **Filtering and sorting** — content and runs support server-side filtering

### Replacing with a Real Backend

To swap the mock API for a real HTTP backend:

1. Create a new API client (e.g., `src/api/`) using `fetch` or `axios`
2. Update `src/lib/api.ts` to import from your real client instead of `@/mock-api`
3. Maintain the same function signatures for a drop-in replacement
4. Remove `src/mock-api/` when no longer needed

Example:

```ts
// src/api/feedback.ts
export async function listFeedback(workspaceId: string): Promise<FeedbackEvent[]> {
  const res = await fetch(`/api/workspaces/${workspaceId}/feedback`);
  return res.json();
}
```

## Tech Stack

| Technology | Purpose |
|------------|---------|
| React 19 | UI framework |
| TypeScript 5.9 | Type safety |
| Vite 6 | Build tool and dev server |
| Tailwind CSS v4 | Utility-first styling |
| React Router v7 | Client-side routing |
| TanStack Query v5 | Data fetching, caching, and mutations |
| Zustand v5 | Global state management |
| React Hook Form + Zod | Form handling and validation |
| Motion (Framer) | Animations and transitions |
| Lucide React | Icon library |
| React Markdown | Markdown rendering in report threads |
