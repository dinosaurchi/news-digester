# Frontend Handoff — Admin UI MVP (Vite, production-ready, mock API first)

## Goal

Build a production-ready frontend for the SME news/reporting Admin UI using Vite.
This pass is frontend-only and should use a mock API contract layer so the UI can be integrated with the real backend later without major refactor.

The frontend should look and behave like a polished internal SaaS product, with strong UX, clean information hierarchy, and robust state handling.

The app manages customer workspaces that collect feeds, process content, and generate scheduled reports.
The main output is a Report Thread UI that behaves like a chat app: when the system generates a report, it appears as a thread message; the admin can give feedback directly in the thread and receive response messages from the agent. Each report message also has thumb up / thumb down feedback controls.

---

## Hard requirements

- Use Vite
- Use React
- Use TypeScript
- Use a modern, maintainable component structure
- Use a mock API contract layer, not ad hoc local hardcoded state inside pages
- Make the UI feel production-ready
- Cover all pages/sections discussed:
  - Workspaces list
  - Workspace overview
  - Profile / Business settings
  - Feeds / Sources
  - Content inspection
  - Report Thread
  - Runs / Logs
  - Feedback / Preferences
  - Settings / Config
- Report thread must feel like a chat app
- Use GitHub-style Markdown rendering for report content
- Include loading / empty / error states
- Include responsive behavior for desktop-first usage
- Build in a way that real backend integration later is straightforward

---

## Product framing

This is an Admin UI first MVP for a system that:
1. lets admin users create a workspace per customer
2. configure business profile, priorities, feeds, and schedule
3. fetch/process news and articles in the backend
4. generate reports
5. show those reports in the frontend
6. allow admin feedback/tuning
7. later add outbound email delivery

For this frontend pass, backend behavior is mocked, but the UI should behave like a real product.

---

## UX principles

Apply strong industrial UI/UX best practices:

- clear navigation and information hierarchy
- shallow learning curve for first-time users
- consistent spacing, typography, and interaction patterns
- obvious system status and state transitions
- avoid clutter
- optimize for fast operator workflows
- make debugging and inspection easy
- preserve good readability for dense information tables
- minimize modal overuse
- use inline affordances where practical
- keep forms structured and scannable
- favor explicit labels over ambiguous icons
- support long-running operational usage

The interface should feel like a serious internal operations product, not a toy demo.

---

## Recommended frontend stack

Required:
- Vite
- React
- TypeScript

Recommended:
- React Router
- TanStack Query
- Zustand or lightweight local store where appropriate
- Tailwind CSS
- shadcn-style component patterns or equivalent accessible component system
- react-hook-form + zod for forms
- react-markdown for Markdown rendering
- a table solution appropriate for dense admin UIs
- date formatting utilities
- class-variance-authority or similar if useful

Do not over-engineer. Keep the architecture clean and practical.

---

## App structure

## Top-level routes

Implement these top-level routes:

- `/` → redirect to `/workspaces`
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

You may also implement nested routing if cleaner.

---

## Main layout

Create a professional desktop-first app shell:

- left sidebar navigation
- top header bar
- main content area
- optional right-side contextual panel where useful

### Sidebar
Should include:
- Workspaces
- selected workspace section nav:
  - Overview
  - Profile
  - Feeds
  - Content
  - Reports
  - Runs
  - Feedback
  - Settings

### Header
Should include:
- current page title
- workspace switcher when inside workspace pages
- global search placeholder
- Run now action
- user menu placeholder

---

## Pages and sections

## 1. Workspaces page

Purpose:
- list customer workspaces
- create workspace
- inspect operational status quickly

Must include:
- page header
- create workspace button
- searchable/filterable list or table
- workspace cards or rows showing:
  - workspace name
  - customer/company
  - status
  - next run
  - last report
  - feed count
  - unread alerts/issues indicator if applicable

Actions:
- open workspace
- run now
- quick view

Empty state:
- helpful CTA to create first workspace

---

## 2. Workspace overview page

Purpose:
- provide operational snapshot

Must include:
- summary cards:
  - workspace health
  - active feeds
  - content items today
  - reports generated
  - next scheduled run
- recent reports preview
- recent runs preview
- top signals or highlighted content preview
- quick actions:
  - run now
  - open latest report
  - edit profile
  - manage feeds

---

## 3. Profile page

Purpose:
- configure business context for report relevance

Sections:
- business identity
- business description
- products/services
- competitors
- priority themes/topics
- excluded topics
- notes for report relevance

UX requirements:
- structured form layout
- support list-style editing for competitors/themes
- validation states
- save bar or clear save action
- unsaved changes warning

---

## 4. Feeds page

Purpose:
- manage input sources

Must include:
- feed list/table
- add feed action
- edit feed
- enable/disable toggle
- source type
- health/status
- last fetched time
- fetch cadence
- tags/category if applicable

Support feed types like:
- RSS
- website/news source
- competitor page
- blog/paper source

UX:
- side sheet or drawer for add/edit is preferred over disruptive full-page flow
- clear validation and test status

---

## 5. Content page

Purpose:
- inspect fetched/processed content items and why they were included or excluded

Must include:
- dense, filterable table/list
- filters:
  - date range
  - source
  - status
  - score range
  - included in report
- columns:
  - title
  - source
  - published date
  - content type
  - local relevance score
  - LLM score
  - final score
  - status
  - cluster id
- row click opens detail panel/page

Content item detail should include:
- metadata
- extracted snippet/body preview
- scores and explanations
- cluster relation
- report inclusion info
- feedback hooks if useful

This page is critical for debugging and should feel operator-friendly.

---

## 6. Reports page

Purpose:
- list generated report threads

Must include:
- reports/threads list
- filters by date/status
- latest report highlight
- thread status
- created time
- report period
- run id
- open thread action

This should not just be a plain document list. It should clearly suggest that reports are conversational threads.

---

## 7. Report Thread page

This is one of the most important pages.

### Core UX
The report detail should behave like a chat app thread:

- vertical conversation timeline
- system/agent messages
- user/admin feedback messages
- clear timestamp separation
- sticky composer at bottom
- scrolling conversation area
- readable markdown messages

### Message types
Support at least:
- system report message
- system follow-up/clarification message
- user feedback message
- agent response message
- system status message

### Initial thread behavior
When a report is generated, the system posts a report message into the thread.

That report message should support:
- rendered Markdown preview
- source items used
- metadata header
- thumb up
- thumb down
- optional actions:
  - copy markdown
  - regenerate
  - inspect sources

### Feedback UX
The user can:
- type feedback directly in the thread composer
- send free-text comments
- click thumb up/down on each report message

After feedback is sent, the thread should display:
- the user feedback message
- a mocked agent response message

The mocked agent responses should feel realistic, such as:
- acknowledging feedback
- summarizing what changed
- saying future reports will prioritize/deprioritize certain topics

### Thread layout
Recommended structure:
- left thread/message stream
- optional right info panel for selected message/report metadata and source links

### Markdown rendering
Use GitHub-style readable Markdown rendering for report content:
- headings
- bullets
- links
- tables if needed
- code block styling is less important but still should look clean

### Important UX requirements
- good reading width for markdown
- comfortable spacing between messages
- obvious difference between user and system messages
- sticky composer
- keyboard-friendly send behavior
- loading states when sending feedback
- error retry state

---

## 8. Runs page

Purpose:
- operational transparency and debugging

Must include:
- list/table of runs
- run type
- status
- started at
- duration
- affected counts
- error indicator
- row click to open detail

Run detail panel/page should show:
- step timeline
- log snippets
- errors
- links to generated reports or affected content items

---

## 9. Feedback page

Purpose:
- inspect and manage captured feedback and preference adjustments

Must include:
- feedback event list
- useful/not useful breakdown
- topic preference summary
- source preference summary
- entity preference summary
- report style preferences

This page should feel more like a management and transparency view than a raw database dump.

---

## 10. Settings page

Purpose:
- manage workspace-specific operational/configuration settings

Include sections like:
- schedule configuration
- report generation settings
- digest/report style settings
- thresholds and defaults
- retention/display settings
- future email delivery placeholders
- dangerous actions / archive workspace

Even if some settings are not functional yet, the UI should make sense and be ready for future integration.

---

## Mock API contract layer

Implement a dedicated mock API layer with typed DTOs and realistic fixtures.

### Rules
- no page should hardcode business data inline
- all data should flow through typed service hooks or API client modules
- mock API should simulate latency
- mock API should simulate success, empty, and error states where appropriate
- mock data should look realistic and internally consistent

### Suggested domains
Create mock contract modules for:
- workspaces
- profile
- feeds
- content
- reports
- report threads/messages
- runs
- feedback
- settings

### Required mock behaviors
Support realistic mocked actions:
- list workspaces
- create workspace
- update workspace profile
- list/add/edit feeds
- list content items
- list reports
- get report thread
- send thread feedback message
- thumb up/down report message
- list runs
- get run detail
- update settings
- run now

### Important contract rule
Design the API layer so later it can be swapped to real HTTP calls with minimal surface change.

---

## Suggested domain types

Include strong TypeScript types for core entities such as:

- Workspace
- WorkspaceSummary
- WorkspaceProfile
- FeedSource
- ContentItem
- ContentItemDetail
- ReportThread
- ReportMessage
- RunSummary
- RunDetail
- FeedbackEvent
- WorkspaceSettings

You do not need to model the entire future backend, but types should be coherent and realistic.

---

## Visual design direction

The UI should feel like:
- modern internal SaaS
- calm, information-dense but readable
- operational and trustworthy
- polished enough for real demo use

### Styling guidance
- keep color usage restrained
- strong typography hierarchy
- clear card/table/panel boundaries
- visible but not loud status chips
- consistent spacing scale
- thoughtful empty states
- accessible contrast
- avoid gimmicky gradients or flashy visuals

---

## State handling requirements

Handle these states carefully:
- initial loading
- page-level loading
- table loading
- optimistic UI where appropriate
- empty states
- validation errors
- API failure states
- retry affordances
- unsaved changes states

This must not feel like a static mockup.

---

## Responsiveness requirements

Primary target is desktop/laptop admin usage, but basic tablet support should still be reasonable.

Required:
- sidebar collapse behavior
- tables remain usable
- thread page remains readable
- drawers/sheets work on narrower widths

Do not spend time making this mobile-first.

---

## Accessibility requirements

Apply good defaults:
- semantic structure
- keyboard navigation for major flows
- accessible labels
- focus states
- buttons and toggles with proper semantics
- adequate contrast
- form validation messaging

---

## Implementation passes

Keep the number of passes small. Use these passes.

## Pass 1 — App shell, routing, workspace foundation
Implement:
- Vite app setup
- routing
- app shell
- sidebar + header
- shared UI primitives
- workspace list page
- workspace overview page
- mock API foundation
- typed DTOs
- loading / empty / error patterns

Acceptance:
- app feels like a coherent product shell
- workspace list and overview are polished
- all data comes from mock API layer
- navigation works cleanly

---

## Pass 2 — Core configuration pages
Implement:
- Profile page
- Feeds page
- Settings page
- forms
- list editing UX
- add/edit feed flows
- save states
- validation
- unsaved changes handling

Acceptance:
- admin can realistically configure a workspace
- forms feel production-ready
- feed management is polished and believable
- settings page is coherent and extensible

---

## Pass 3 — Operational visibility pages
Implement:
- Content page
- content filters
- content detail panel/page
- Runs page
- run detail view
- realistic status chips
- debug-friendly visual hierarchy

Acceptance:
- admin can inspect what happened operationally
- content/runs pages are dense but readable
- filters and tables are practical for real use

---

## Pass 4 — Report Thread UX
Implement:
- Reports list page
- Report Thread page
- chat-style thread UX
- markdown rendering
- sticky composer
- feedback sending flow
- thumb up/down on report messages
- mocked agent response behavior
- source item side panel or detail section

Acceptance:
- report threads feel like a polished chat-style workflow
- markdown reports are highly readable
- feedback loop feels natural
- thumbs up/down interactions are clear and useful

---

## Pass 5 — Polish and QA hardening
Implement:
- cross-page consistency cleanup
- edge states
- responsive cleanup
- keyboard/focus polish
- error/retry polish
- fixture consistency cleanup
- minor visual polish

Acceptance:
- frontend looks demo-ready
- interaction quality is consistent
- major empty/loading/error cases are covered
- code is maintainable and ready for backend integration

---

## Technical guardrails

- keep components modular
- avoid giant page components
- separate presentational components from data hooks when helpful
- prefer typed reusable UI patterns
- keep mock API isolated from page rendering logic
- avoid hardcoded magic strings scattered across pages
- do not overcomplicate global state
- prefer simple and clear code over framework cleverness

---

## Deliverables

Produce:
1. a complete Vite React TypeScript frontend
2. mock API contract layer
3. realistic fixtures
4. all pages/routes above
5. production-ready UI/UX polish
6. README with:
   - how to run
   - app structure
   - mock API design
   - how to swap to real backend later

---

## Nice-to-have, only if low cost

- command palette or quick search placeholder
- theme-ready structure
- reusable status chip system
- reusable empty/error state components
- split-pane resizing on thread/content views if easy

Do not let nice-to-haves reduce core quality.

---

## Explicitly out of scope

Do not implement:
- real backend
- real authentication
- real ingestion workers
- real ML/LLM integration
- real persistence
- real email sending
- real websocket/live updates unless trivial to mock cleanly

The priority is a strong frontend foundation with realistic mocked behavior.

---

## Final instruction

Build this as if it will be shown to stakeholders soon and later integrated with a real backend.
Prioritize:
- production-ready UX
- clean architecture
- realistic mocked workflows
- excellent report thread experience
- maintainable codebase
