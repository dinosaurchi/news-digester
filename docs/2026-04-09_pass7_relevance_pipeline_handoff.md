# Pass 7 Continuation Handoff — Relevance Pipeline and Report Quality

## Purpose

This document is the implementation handoff for continuing **Pass 7** after the completion of Pass 6.

It expands the high-level Pass 7 section in:

- [docs/2026-04-08_backend_api_handoff_sme_news.md](/workspace/projects/sme-news-admin/docs/2026-04-08_backend_api_handoff_sme_news.md#L1105)

The original handoff remains the source of roadmap intent.
This document is the source of execution detail for the remaining Pass 7 work.

---

## Current baseline

As of this handoff:

- Passes 1 through 5.5 are complete enough for continued backend work
- Pass 6 is implemented:
  - real content ingestion skeleton exists
  - `run-now` works
  - content items persist
  - run events persist
  - stub report generation works
  - Celery worker and Beat are wired
- frontend/backend contract stabilization is complete enough to continue
- the app is ready for Pass 7, but Pass 7 itself is **not** yet implemented

What is still true today:

- scoring is mostly stubbed
- dedup/clustering is not yet real
- report generation is still deterministic stub output
- feedback is persisted but not yet meaningfully fed into relevance/report quality

---

## Pass 7 objective

Turn the working Pass 6 pipeline foundation into the first **meaningfully useful intelligence pipeline**.

At the end of Pass 7:

- the system should ingest real source data
- cluster/deduplicate related content
- apply cheap relevance filtering before expensive reasoning
- persist interpretable scores and reasons
- shortlist the strongest items
- generate a materially better report from shortlisted items
- preserve traceable content-to-report linkage
- keep the current frontend API contract stable

Pass 7 should improve usefulness, not just add complexity.

---

## Explicit non-goals

Do **not** do these in this handoff unless required to complete the scoped Pass 7 work:

- major auth changes
- frontend redesign
- email delivery
- websockets / real-time updates
- autonomous agent framework
- advanced learning-to-rank
- bandits / online learning
- deep personalization engine
- multi-LLM orchestration
- production-grade observability platform
- Pass 8-style roadmap expansion

Keep the work centered on relevance and report quality only.

---

## Required constraints

- preserve current frontend DTOs and endpoint shapes
- do not reintroduce frontend mock/demo logic
- keep stub fallbacks backend-owned if needed
- keep `run-now` working end to end throughout implementation
- keep content/report/thread linkage inspectable
- prefer thin vertical slices over a single large rewrite
- every pass below must leave the branch in a runnable state

---

## Pass breakdown

Implement Pass 7 in these sub-passes.

Do not skip ahead if a prior sub-pass is unstable.

### Pass 7.1 — Content dedup and clustering foundation

#### Scope

Add the first real grouping layer so the system can reason about related items instead of treating every fetched item independently.

#### Implementation tasks

- define a deterministic clustering/dedup strategy for this phase
- use lightweight features first:
  - normalized URL/domain/title similarity
  - publication time proximity where useful
  - simple text similarity
- assign or update `cluster_id` on `ContentItem`
- persist enough cluster metadata to inspect what happened
- mark likely duplicates versus lead items where useful
- keep the implementation explainable and testable

#### Expected output

- related articles from the same story should group together often enough to reduce noisy repetition
- content detail and run inspection should remain understandable

#### Acceptance criteria

- related ingested items can share a cluster
- obviously duplicated items no longer behave as fully independent top candidates
- cluster linkage is persisted and visible through existing inspection paths
- tests pass

---

### Pass 7.2 — Cheap relevance filtering and scoring

#### Scope

Add the first meaningful relevance layer before any expensive LLM step.

#### Implementation tasks

- implement rule-based filtering first
  - workspace keywords / themes
  - competitor/product mentions when available
  - excluded topics
  - simple freshness/source heuristics if useful
- implement BM25-style lexical relevance scoring
- implement embeddings similarity scoring if feasible within current stack
- produce a combined cheap-score stage
- persist score components and reasons on content items
- write clear inclusion/exclusion reasons that are operator-readable
- keep thresholds configurable through workspace settings where possible

#### Expected output

- low-signal items should start getting filtered out for concrete reasons
- strong items should have interpretable score breakdowns

#### Acceptance criteria

- content items persist score breakdowns and reasons
- inclusion/exclusion is no longer just the current first-five stub
- filtering remains deterministic when LLM is unavailable
- tests pass

---

### Pass 7.3 — Shortlist generation

#### Scope

Choose the final candidate set for report generation from the cheaper upstream signals.

#### Implementation tasks

- define shortlist selection rules from clustered/scored content
- avoid selecting multiple near-duplicate items when one representative is enough
- cap shortlist size using workspace settings or a sensible default
- if using an LLM at this stage:
  - only run it after cheap filtering
  - use it for refinement/reasoning, not first-pass screening
  - persist shortlist rationale
- define strict fallback behavior when LLM/provider fails:
  - no crash
  - fallback to cheap-score ranking
  - persist fallback marker or reason in run events/logs where appropriate

#### Expected output

- each run produces a defensible shortlist of items that matter most

#### Acceptance criteria

- shortlist generation works with and without LLM availability
- shortlist size is controlled
- shortlist reasons are persisted or traceable
- tests pass

---

### Pass 7.4 — Report generation quality upgrade

#### Scope

Replace the current deterministic stub report with a real report generation path based on shortlisted content.

#### Implementation tasks

- generate real markdown report structure from shortlisted items
- keep output compatible with the current report/thread frontend UX
- include:
  - title
  - period
  - top themes / highlights
  - concrete source-backed narrative
- ensure report messages retain source item references
- preserve report/thread/message persistence model already used by the frontend
- if using an LLM:
  - keep prompt inputs bounded and traceable
  - add fallback generation if provider fails
  - do not lose the report entirely on provider failure

#### Expected output

- reports should read like actual digests rather than placeholder summaries
- source inspection from the thread UI must still work

#### Acceptance criteria

- generated reports are materially different from the current stub body
- source links in report/thread messages resolve to content items
- report/thread/message persistence remains stable
- regenerate path still works with the new report format
- tests pass

---

### Pass 7.5 — Feedback-aware quality hooks

#### Scope

Use existing feedback persistence to improve traceability and prepare later tuning work without overbuilding.

#### Implementation tasks

- connect thumbs/comment/topic/source feedback into inspectable preference signals
- make sure feedback can be associated with relevant report/content context
- optionally expose lightweight influence markers in score/report generation metadata
- do not implement advanced learning loops yet

#### Expected output

- feedback should have visible downstream relevance context, even if the effect is still simple

#### Acceptance criteria

- feedback influence is at least traceable in stored data or run/report metadata
- no existing feedback endpoints/regressions are introduced
- tests pass

---

### Pass 7.6 — Final hardening, redeploy, and QA

#### Scope

Close Pass 7 with branch-wide validation and manual verification.

#### Required steps

- run backend tests
- run frontend tests
- run production build
- redeploy with `make up`
- verify all relevant containers are healthy
- QA both API and Web UI behavior after redeploy

#### Acceptance criteria

- all tests pass
- deployment succeeds
- Web UI and API work properly with the updated Pass 7 behavior
- branch is safe to continue only after QA is complete

---

## Data and persistence expectations

By the end of Pass 7, persisted data should include most of the following where appropriate:

- cluster identity and related-item grouping
- score components
- final score
- inclusion reason
- exclusion reason
- shortlist rationale
- report generation source references
- fallback markers when LLM/provider is unavailable
- run-event detail that explains the major pipeline stages

Do not hide reasoning only inside ephemeral logs if it should be operator-inspectable later.

---

## Suggested implementation order inside the codebase

Recommended backend change order:

1. extend reusable pipeline-step helpers and shared pipeline service
2. add clustering/dedup helpers and persistence
3. add cheap scoring and threshold logic
4. add shortlist selection
5. upgrade report generation
6. add feedback-aware hooks
7. finish QA, docs, and cleanup

Do not start by rewriting the API layer unless contract preservation requires it.

---

## Testing requirements

### Unit tests

Add unit coverage for:

- clustering/dedup helpers
- score calculation helpers
- shortlist selection
- report markdown builder
- fallback behavior when upstream/LLM calls fail

### API / integration tests

Add integration coverage for:

- `run-now` producing clustered/scored content
- content detail exposing useful persisted fields
- report creation from shortlisted content
- report/thread/message linkage
- regenerate behavior still working
- feedback persistence remaining stable

### Contract tests

Verify that the frontend-facing DTO shapes remain stable for:

- content list/detail
- reports list/detail/thread
- run detail
- feedback endpoints

### Required test commands

Run at minimum:

```bash
cd backend && python -m pytest --tb=short
npm test -- --run
npm run build
```

---

## Required redeploy and QA

After the implementation is complete, redeploy and QA the live stack.

### Redeploy

```bash
make up
docker compose ps
```

### API QA checklist

Verify at minimum:

- `GET /api/health` succeeds
- `POST /api/workspaces/{id}/run-now` succeeds
- run detail shows meaningful steps and links
- content list/detail show real scores/reasons/clusters when expected
- report list/thread load successfully
- report message source inspection resolves content items
- regenerate still works if supported for the generated thread
- feedback actions still persist and read back correctly

### Web UI QA checklist

Verify at minimum in the browser:

- workspace overview still loads
- content page loads and shows useful scoring/cluster information where exposed
- reports page loads
- report thread renders the upgraded report correctly
- source inspection panel still works
- runs page shows meaningful step timeline and generated links
- feedback page still loads and persists actions
- no frontend runtime errors appear in the main Pass 7 flows

If browser access is unavailable in the execution environment, document that limitation explicitly and still complete all container/API QA that is possible.

---

## Final acceptance criteria for Pass 7

Pass 7 is complete only when all of the following are true:

- dedup/clustering exists and is persisted
- cheap relevance filtering exists and is persisted
- content scores and reasons are inspectable
- shortlist generation is real and no longer just first-N stub behavior
- report generation is materially improved from the current deterministic stub
- content-to-report linkage is traceable
- regenerate still behaves correctly
- feedback persistence still works and has at least basic downstream traceability
- backend tests pass
- frontend tests pass
- production build passes
- `make up` redeploy succeeds
- API QA passes
- Web UI QA passes or any environment limitation is explicitly documented

Only after that should Pass 7 be considered complete.

---

## Deliverables

Produce:

1. implemented Pass 7 code in thin, reviewable commits
2. updated automated tests
3. any required migration/model updates
4. updated QA notes documenting redeploy and API/Web UI verification
5. a short completion note explicitly stating whether Pass 7 is done or what remains

---

## Final instruction

Do not treat Pass 7 as “make it smarter somehow”.

Treat it as:

- deterministic pipeline improvements first
- LLM usage only where it adds clear value
- persistence and inspectability throughout
- frontend contract safety throughout
- redeploy and QA before calling it complete
