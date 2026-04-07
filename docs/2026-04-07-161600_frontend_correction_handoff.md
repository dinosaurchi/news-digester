# Correction Handoff — Fix Frontend to Match Admin UI MVP Spec

## Goal

Fix the current frontend implementation so it matches the intended **frontend-only Admin UI MVP** spec.

The current implementation is promising, but it has several major mismatches:

1. it used **Next.js** instead of **Vite**
2. it drifted into **auth / local DB / backend-ish scope**
3. several pages are present but still too shallow for the intended operator workflow
4. the mock API contract layer is too monolithic
5. the report thread UX needs to be more production-ready

This handoff is for **correcting the existing implementation**, not starting over blindly.

---

## Non-negotiable correction targets

The fixed implementation must satisfy all of the following:

- use **Vite**
- remain **frontend-only**
- use a **mock API contract layer**
- remove backend-ish drift from this pass
- cover all required pages/sections
- keep the **Report Thread** as a chat-style experience
- improve operator-grade debugging UX for Content / Runs / Feedback
- remain maintainable and ready for real backend integration later

---

## Pre-implementation decisions and dependency map

Before starting Pass 1, the following decisions are locked and must be applied consistently:

### Framework and tooling decisions

| Topic | Decision |
|---|---|
| Build tool | Vite (with `@vitejs/plugin-react`) |
| Routing | React Router **v6** (`createBrowserRouter`, `<RouterProvider>`) |
| CSS framework | Tailwind CSS **v4** — use `@tailwindcss/vite` Vite plugin, NOT `@tailwindcss/postcss` |
| State (client) | Keep **Zustand** for sidebar state and current workspace tracking |
| Animations | Keep **motion** (`motion/react`) for page transitions |
| Login screen | Keep as a **hardcoded mock login** (no real auth, no API call). Credentials are purely UI-side. Navigate directly to `/workspaces` on submit. |
| Environment vars | Drop all backend env vars (`JWT_SECRET`, `GEMINI_API_KEY`). Any future frontend-only vars must use `VITE_` prefix and `import.meta.env`. No `.env` file is required to run the app. |

### Dependency changes

**Remove from `package.json`:**
- `next`
- `drizzle-orm`
- `drizzle-kit`
- `better-sqlite3`
- `jose`
- `bcryptjs`
- `cookie`
- `@google/genai`
- `@types/bcryptjs`
- `@types/better-sqlite3`
- `@types/cookie`
- `eslint-config-next`
- `firebase-tools`
- `@tailwindcss/postcss` (replaced by `@tailwindcss/vite`)

**Add to `package.json`:**
- `vite`
- `@vitejs/plugin-react`
- `@tailwindcss/vite`
- `react-router-dom`
- `@types/react-router-dom` (if needed)

**Keep as-is:**
- `react`, `react-dom`
- `@tanstack/react-query`
- `react-hook-form`, `@hookform/resolvers`, `zod`
- `tailwindcss`, `@tailwindcss/typography`, `postcss`, `autoprefixer`
- `lucide-react`
- `react-markdown`
- `motion`
- `clsx`, `tailwind-merge`, `class-variance-authority`
- `date-fns`, `uuid`
- `zustand`
- `typescript`, `eslint`

### Vite config requirements

`vite.config.ts` must include:
- `@vitejs/plugin-react` plugin
- `@tailwindcss/vite` plugin
- Path alias: `@` → `src/` (mirror the existing `tsconfig.json` alias)

`index.html` must exist at the project root (Vite entry point), referencing `src/main.tsx`.

`src/main.tsx` bootstraps `<RouterProvider>` with the app router.

---

## Current implementation issues to fix

## 1. Wrong framework
The app is currently built with **Next.js App Router**.
This is incorrect for the requested scope.

### Must fix
- migrate frontend to **Vite + React + TypeScript** (see pre-implementation decisions above for exact config)
- replace all `next/navigation` and `next/link` usages (`useRouter`, `usePathname`, `Link`) with **React Router v6** equivalents (`useNavigate`, `useLocation`, `useParams`, `<Link>`)
- replace Next.js `app/` directory structure with Vite `src/pages/` structure
- remove `next.config.ts` and all Next.js-specific assumptions
- add `index.html` at project root as Vite entry point

---

## 2. Scope drift into backend/auth
The current implementation includes auth/db/backend-ish pieces that do not belong in this pass.

Examples include:
- login flow
- auth APIs
- DB-related setup
- drizzle config
- sqlite usage
- seed scripts
- server-side coupling

### Must fix
- remove all files: `lib/db/`, `lib/auth.ts`, `seed.ts`, `drizzle.config.ts`, `app/api/`
- remove all backend dependencies (see pre-implementation decisions — dependency changes)
- keep the login screen but make it **purely mock**: hardcode acceptance of any credential (or a fixed dummy credential), and navigate to `/workspaces` on submit — no API call, no JWT, no cookie
- remove the auth check from `AppLayout` — it currently calls `/api/auth/me` on every route change; replace with a trivial mock session state
- do not require a real server, DB, or auth flow to run the frontend

The final result must run with `vite dev` only — no database, no backend process, no migration step.

---

## 3. Mock API layer too monolithic
The current mock API/data setup is too centralized and not modular enough.

### Must fix
Split the mock contract layer by domain. Use something like:

- `src/mock-api/workspaces.ts`
- `src/mock-api/profile.ts`
- `src/mock-api/feeds.ts`
- `src/mock-api/content.ts`
- `src/mock-api/reports.ts`
- `src/mock-api/reportThreads.ts`
- `src/mock-api/runs.ts`
- `src/mock-api/feedback.ts`
- `src/mock-api/settings.ts`

Also add:
- `src/types/...`
- `src/lib/api-client/...` or equivalent
- typed service hooks

The goal is to make later real backend replacement straightforward.

---

## 4. Pages exist but are too shallow
The current implementation has many required pages, but several of them are still not deep enough for realistic operator workflows.

This must be fixed especially for:
- Content
- Runs
- Feedback
- Settings
- Report Thread

---

## 5. Report Thread needs stronger production UX
The report thread is the strongest part of the current app, but it still needs improvement.

### Must improve
- clearer thread-level header
- report metadata block
- richer message types
- better distinction between system report, user feedback, and agent response
- source inspection side panel or equivalent detail view
- better empty/sending/error states
- more realistic feedback loop behavior

---

## Final desired architecture

The corrected frontend should be:

- **Vite** (with `@vitejs/plugin-react` + `@tailwindcss/vite`)
- **React 19**
- **TypeScript**
- **Tailwind CSS v4**
- **React Router v6**
- **TanStack Query v5**
- **Zustand** (client state — sidebar, active workspace)
- **motion** (page transitions)
- mock API contract layer
- strongly typed domain models
- desktop-first internal SaaS UX
- production-ready visual quality
- easy to integrate with real backend later

---

## Technical requirements

## Required stack
- Vite (with `@vitejs/plugin-react`)
- React 19
- TypeScript
- React Router **v6** (`react-router-dom`)
- TanStack Query v5
- Tailwind CSS **v4** (via `@tailwindcss/vite` plugin, not PostCSS)
- `@tailwindcss/typography` (for markdown prose rendering)
- react-hook-form + zod
- react-markdown
- Zustand (for sidebar collapse state and active workspace tracking)
- motion (`motion/react`) for page transitions
- a clean table/data-grid approach suitable for admin UIs

## Preferred patterns
- route-driven page structure
- modular components
- domain-based data hooks
- typed DTOs
- reusable loading / empty / error components
- reusable status chips
- drawer/sheet or side-panel patterns for detail inspection

---

## Out of scope

Do not implement:
- real backend
- real auth
- real database
- real ingestion workers
- real persistence
- real LLM integration
- real email delivery

This remains a frontend-first, mock-driven implementation.

---

## Implementation passes

Keep the passes focused. Do not combine too much into one pass.

# Pass 1 — Replatform to Vite and remove backend drift

## Scope
Convert the app from Next.js-style structure to **Vite + React + TypeScript** and remove backend/auth/server drift.

> **Scope warning:** This pass is larger than it appears. Every page file currently imports from `next/navigation` or `next/link`. The `AppLayout` runs an async auth check on every route change. All of these must be replaced. Allocate accordingly — this is a full surgical migration, not a config swap.

## Required changes

### Project setup
- delete `next.config.ts`, `app/` directory, `lib/db/`, `lib/auth.ts`, `seed.ts`, `drizzle.config.ts`
- create `index.html` at project root (Vite entry, references `src/main.tsx`)
- create `vite.config.ts`:
  ```ts
  import { defineConfig } from 'vite'
  import react from '@vitejs/plugin-react'
  import tailwindcss from '@tailwindcss/vite'
  import path from 'path'

  export default defineConfig({
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: { '@': path.resolve(__dirname, 'src') },
    },
  })
  ```
- update `tsconfig.json` `paths` to match (already has `@/*` → `src/*`, verify it stays)
- update `package.json` scripts: `"dev": "vite"`, `"build": "vite build"`, `"preview": "vite preview"`

### Routing
- replace all `next/navigation` and `next/link` imports with React Router v6 equivalents:
  - `useRouter().push(path)` → `useNavigate()(path)`
  - `useRouter().back()` → `useNavigate()(-1)`
  - `usePathname()` → `useLocation().pathname`
  - `useParams()` → `useParams()` (same, different import)
  - `<Link href=...>` → `<Link to=...>`
- create `src/router/index.tsx` with `createBrowserRouter` defining all routes
- `src/main.tsx` renders `<RouterProvider router={router} />`

### Auth removal
- remove the `/api/auth/me` call from `AppLayout` entirely
- replace with a trivial mock session: store a boolean `isLoggedIn` in Zustand, set it to `true` on login form submit, redirect to `/` (→ `/workspaces`) if `false` on protected routes
- the login page accepts any non-empty credentials and sets `isLoggedIn = true`
- no JWT, no cookie, no API call

### Tailwind CSS v4
- remove `@tailwindcss/postcss` from devDependencies
- add `@tailwindcss/vite` to devDependencies
- update `src/globals.css` (or `src/index.css`) to use `@import "tailwindcss"` — v4 does not use `@tailwind base/components/utilities` directives
- keep `@tailwindcss/typography` plugin

### Component preservation
- keep `components/sidebar.tsx`, `components/header.tsx`, `components/providers.tsx`
- keep `components/app-layout.tsx` after removing the auth check
- keep `lib/utils.ts`, `lib/store.ts` (Zustand — keep for sidebar and workspace state)
- keep `lib/api.ts` as-is for now (Pass 2 will split it)
- keep `lib/types.ts` as-is for now (Pass 2 will expand it)

## Minimum resulting structure

- `index.html` (project root)
- `vite.config.ts`
- `src/main.tsx`
- `src/App.tsx` (or inline in router)
- `src/router/index.tsx`
- `src/pages/...`
- `src/components/...`
- `src/mock-api/...` (placeholder until Pass 2)
- `src/types/...`
- `src/lib/...`

## Acceptance criteria
- `vite dev` starts the app with no errors
- `vite build` produces a clean production build
- no Next.js package remains in `package.json`
- no real backend/db/auth is required to run
- navigation works correctly with React Router v6
- current pages still exist or are scaffolded
- no Next.js runtime dependency remains
- no backend-ish coupling remains in the frontend pass
- mock login works (any credentials → `/workspaces`)
- Tailwind v4 styles render correctly
- `@` path alias works in all imports

---

# Pass 2 — Clean mock API contracts and type system

## Scope
Refactor the data layer into a modular, domain-based mock API contract system.

## Required changes
Create strong domain types such as:
- Workspace
- WorkspaceSummary
- WorkspaceProfile
- FeedSource
- ContentItem
- ContentItemDetail
- ReportThread
- ReportMessage
- ReportSummary
- RunSummary
- RunDetail
- FeedbackEvent
- WorkspaceSettings

Create domain-based mock modules:
- workspaces
- profile
- feeds
- content
- reports
- reportThreads
- runs
- feedback
- settings

Create realistic fixtures:
- multiple workspaces
- varied feed states
- different content statuses/scores
- multiple report threads
- multiple runs with mixed success/failure
- useful feedback examples
- settings variations

Ensure:
- pages do not hardcode business data inline
- all pages consume the contract layer
- latency is simulated
- loading/empty/error states are testable

## Acceptance criteria
- no giant single mock API file
- all data comes from typed domain contracts
- fixtures are realistic and internally consistent
- later real backend swap feels straightforward

---

# Pass 3 — Strengthen app shell, IA, and workspace flows

## Scope
Make the navigation and page structure fully aligned with the intended information architecture.

## Required pages/routes
- `/workspaces`
- `/workspaces/:workspaceId`
- `/workspaces/:workspaceId/profile`
- `/workspaces/:workspaceId/feeds`
- `/workspaces/:workspaceId/content`
- `/workspaces/:workspaceId/reports`
- `/workspaces/:workspaceId/reports/:threadId`
- `/workspaces/:workspaceId/runs`
- `/workspaces/:workspaceId/feedback`
- `/workspaces/:workspaceId/settings`

## Required improvements
- strong sidebar navigation
- header with current page title
- workspace switcher while inside workspace pages
- sensible breadcrumbs if useful
- “Run now” wired through mocked mutation flow
- overview page with useful operational summary cards
- remove or demote distracting global routes that do not fit the IA

## Acceptance criteria
- navigation feels coherent and intentional
- workspace-centered structure is clear
- app shell feels like a real internal SaaS product
- workspace switching is smooth and understandable

---

# Pass 4 — Deepen Profile, Feeds, and Settings pages

## Scope
Make the configuration pages feel production-ready rather than basic placeholders.

## Profile page requirements
Must include:
- business identity
- business description
- products/services
- competitors
- priority themes/topics
- excluded topics
- notes for report relevance

UX requirements:
- structured form sections
- list editing UX for competitors/themes
- validation
- save behavior
- unsaved changes handling

## Feeds page requirements
Must include:
- feed list/table
- add/edit feed flow
- enable/disable toggle
- source type
- health/status
- fetch cadence
- last fetched time
- tags/category if useful
- realistic feed test state or validation status

Use drawer/sheet or similar for add/edit if appropriate.

## Settings page requirements
Must include sections for:
- schedule configuration
- report generation settings
- digest/report style settings
- thresholds/defaults
- retention/display settings
- future email placeholders
- dangerous actions / archive workspace

## Acceptance criteria
- admin can realistically configure a workspace
- forms are polished and readable
- settings page is not shallow
- feed management looks believable and useful

---

# Pass 5 — Deepen Content and Runs operator workflows

## Scope
Upgrade the debugging/inspection pages so they support real operator use.

## Content page requirements
Must include:
- dense but readable filterable table/list
- filters for date, source, status, score, included-in-report
- columns for title, source, published date, content type, local score, LLM score, final score, status, cluster id
- row click to open detail drawer/panel/page

Content detail must include:
- metadata
- extracted snippet/body preview
- score breakdown
- explanation / inclusion reason
- exclusion reason where applicable
- cluster relation view
- linked report inclusion info if present

## Runs page requirements
Must include:
- run list/table
- run type
- status
- started at
- duration
- affected counts
- error indicator

Run detail must include:
- step timeline
- log snippets
- error details
- links to affected reports/content items
- visible distinction between successful vs failed runs

## Acceptance criteria
- Content page feels operator-grade
- Runs page feels useful for debugging, not just decorative
- detail views are practical and readable
- state/status visualization is clear

---

# Pass 6 — Upgrade Reports list and Report Thread UX

## Scope
Make the report workflow one of the best parts of the app.

## Reports list page requirements
Must include:
- list of report threads
- date/status filters
- report period
- created time
- run id
- latest report highlight
- clear “open thread” action

The page should communicate that reports are conversational threads, not just static documents.

## Report Thread page requirements
The report detail must behave like a chat app thread.

### Core thread UX
- vertical conversation stream
- system report messages
- user feedback messages
- agent response messages
- optional status/system messages
- sticky composer
- readable markdown content
- clear visual hierarchy

### Report message requirements
Each report message should support:
- metadata header
- rendered Markdown
- thumb up
- thumb down
- copy markdown action
- regenerate action
- inspect sources action

### Thread-level improvements
Add:
- clearer thread title/header
- report period
- status
- run id
- last updated
- optional side panel for selected message/report metadata/source items

### Feedback flow requirements
When user sends feedback:
- show pending/sending state
- append user message
- return a mocked agent response
- mocked agent response should feel realistic and context-aware

### Message styling requirements
- visually distinguish user vs system/agent
- comfortable reading width for markdown
- clean timestamp presentation
- clean grouping between messages
- clear error/retry state for failed send

## Acceptance criteria
- report thread feels polished and central to the product
- markdown readability is excellent
- source inspection flow exists
- thumbs up/down behavior is clear
- feedback loop feels believable

---

# Pass 7 — Deepen Feedback page and final polish

## Scope
Turn Feedback into a meaningful management/transparency page and then perform final polish across the app.

## Feedback page requirements
Must include:
- feedback event list
- useful/not useful breakdown
- topic preference summary
- source preference summary
- entity preference summary
- report style preferences
- trace from feedback to affected reports/messages where possible

This should not feel like a dump of random cards. It should feel intentionally designed.

## Final polish requirements
- consistent empty states
- consistent loading states
- consistent error handling
- keyboard/focus polish
- desktop-first responsive cleanup
- consistent spacing and typography
- consistent chips/badges/status colors
- remove dead-end UI paths
- ensure all pages feel like one coherent product

## Acceptance criteria
- the app feels demo-ready
- no page feels obviously unfinished
- UI/UX quality is consistent
- frontend code remains maintainable

---

## Design quality bar

The final product should feel like:
- a serious internal SaaS tool
- information-dense but readable
- operational and trustworthy
- useful for daily operator workflows
- polished enough for stakeholder demos

Avoid:
- toy/demo feel
- oversized empty hero layouts
- decorative-only dashboards
- cluttered settings pages
- weak thread readability
- overly flashy visuals

---

## QA checklist

Before considering the work complete, verify:

### Architecture
- Vite is used (`vite dev` starts cleanly, `vite build` succeeds)
- React Router v6 is used for all routing
- Tailwind CSS v4 is used via `@tailwindcss/vite` plugin
- no Next.js dependency remains in `package.json`
- no backend/db/auth requirement remains (no SQLite, no JWT, no bcrypt)
- no `process.env` usage remains; any env vars use `import.meta.env` with `VITE_` prefix
- mock API contract layer is modular (domain-split files)
- domain types are clean and reusable
- `@` path alias resolves correctly in both Vite and TypeScript
- mock login works without any API call

### Navigation
- all required routes exist
- workspace-centered IA is clear
- workspace switching works
- Run now works via mocked mutation

### Pages
- Workspaces page is polished
- Overview page is useful
- Profile/Feeds/Settings are functional and production-ready
- Content and Runs pages support real debugging workflows
- Reports list is clear
- Report Thread is polished and chat-like
- Feedback page is meaningful

### States
- loading states exist
- empty states exist
- error states exist
- retry states exist where relevant
- unsaved changes states exist on forms where needed

### Report thread
- report markdown is highly readable
- thumb up/down works
- feedback send works
- mocked agent response works
- source inspection flow exists

### Code quality
- no giant page components
- no giant monolithic mock file
- shared UI patterns are reused
- code is organized and maintainable

---

## Deliverables

Produce:

1. corrected Vite-based frontend
2. modular mock API contract layer
3. improved typed domain models
4. all required routes/pages
5. upgraded Report Thread UX
6. upgraded Content / Runs / Feedback / Settings pages
7. README explaining:
   - how to run
   - app structure
   - route structure
   - mock API organization
   - how to replace mock API with real backend later

---

## Final instruction

Do not just patch visuals superficially.

The main objectives are:
- correct the architecture
- remove scope drift
- deepen the operator workflows
- make the report thread excellent
- produce a maintainable frontend that matches the intended spec
