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

## Locked implementation decisions for this handoff

The following choices are fixed for Pass 7 unless this document is updated again:

- embeddings strategy: local embeddings first
- LLM provider strategy: one provider only
- LLM provider and model: opencode with `opencode/gpt-5-nano`
- LLM integration style: configurable backend integration, not hardcoded inline client logic
- external reference for adapter-style integration:
  - `https://github.com/dinosaurchi/ai-pm/blob/main/docker-compose.yml#L97`
- failure behavior: fail fast and explicitly when a required Pass 7 stage fails; do not hide failures behind silent fallback output
- dedup/clustering priority: near-duplicate focus first, broader story clustering later
- feedback scope in Pass 7: traceability now, ranking impact later
- infrastructure constraint: avoid heavy infrastructure such as pgvector / ANN indexing unless clearly necessary during Pass 7

These are implementation instructions, not suggestions.

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
- preserve the existing user feedback flow on report threads
- keep the current frontend API contract stable
- support scheduled daily report generation through the existing Celery/Beat path
- fail explicitly when required Pass 7 processing stages fail rather than returning misleading “successful” output

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
- do not hide failed Pass 7 stages behind backend-owned fake success output
- keep `run-now` working end to end throughout implementation
- keep content/report/thread linkage inspectable
- keep report-thread thumbs up/down and message feedback working throughout
- keep scheduled execution working alongside manual `run-now`
- prefer thin vertical slices over a single large rewrite
- every pass below must leave the branch in a runnable state

---

## Technique guidance

This section exists to reduce implementation drift.

### Dedup / clustering

For Pass 7, prioritize **near-duplicate detection** over ambitious broad story clustering.

Prefer this order of techniques:

1. URL canonicalization and exact-match dedup
2. normalized title hashing
3. domain + title similarity heuristics
4. publication-time proximity as a supporting signal
5. local text similarity for borderline cases

Acceptable techniques for this phase:

- URL normalization
- normalized-title fingerprinting
- trigram / token overlap similarity
- MinHash or SimHash if needed
- simple local cosine similarity on embeddings only if it clearly improves duplicate grouping

Avoid in Pass 7 unless clearly required:

- heavy graph clustering systems
- expensive all-to-all semantic clustering without clear bounds
- broad “story clustering” that is too fuzzy to explain

The goal is:

- collapse obvious duplicates first
- keep one representative article when many copies of the same story exist
- only then consider modest broader grouping

### Cheap relevance filtering

Prefer deterministic and inspectable techniques first:

- workspace theme keyword matching
- product / competitor / entity matching
- excluded-topic suppression
- source/domain heuristics where justified
- freshness heuristics where justified
- BM25-style lexical scoring

If embeddings are added in this pass:

- use local embeddings only
- use simple cosine similarity
- keep the implementation bounded and explainable
- do not introduce external embedding APIs for Pass 7
- do not introduce pgvector or ANN search unless a clear Pass 7 need forces it

### LLM usage

LLM usage is allowed only in two places in Pass 7:

- shortlist refinement after cheap filtering
- final report generation from shortlisted content

Do not use the LLM for:

- first-pass screening of all content
- basic dedup decisions that heuristics can handle
- replacing deterministic score persistence with opaque text output

LLM integration requirements:

- use opencode with `opencode/gpt-5-nano`
- make the provider endpoint / adapter / model configurable
- keep one-provider-only scope for Pass 7
- follow an adapter-style integration pattern similar to the referenced `opencode-agent-adapter` deployment
- persist explicit run-event details and error summaries when the LLM path fails

Required failure policy for LLM steps:

- if a required LLM step fails, the run must fail explicitly
- do not silently replace failed LLM output with fake “successful” deterministic output
- do not hide provider/network/authentication/model errors
- persist enough run-event and error-summary detail for operators to understand what failed

### Report generation

Prefer a structured, source-grounded generation flow:

- deterministic report input assembly
- bounded shortlisted context
- structured prompt-to-markdown generation

The report generator must never produce an ungrounded report without preserved source references.

---

## Scheduled daily report generation requirement

Pass 7 must not only support manual `run-now`.
It must also support the normal operating path where the backend consumes collected feeds on a schedule and produces persisted reports.

For this handoff, that means:

- the existing Celery + Beat path remains the scheduling backbone
- workspace schedule settings remain the scheduling source of truth
- daily scheduled execution must be supported
- successful scheduled execution must persist report/thread/message records in the app
- failed scheduled execution must persist explicit run failure state and error details
- scheduled runs must not pretend to have produced a successful report when required stages failed

Out of scope for this handoff:

- email delivery of the report
- real-time push notifications
- advanced orchestration beyond the current scheduler/worker model

---

## Feedback continuity requirement

The current user feedback paths in the report thread must continue to work during and after Pass 7:

- thumbs up/down on report messages
- free-text message feedback in the report chatbox

Pass 7 may make that feedback more traceable downstream, but it must not break:

- persistence
- retrieval
- existing frontend flows
- existing API contracts

This is a release-blocking requirement for Pass 7.

---

## Pass breakdown

Implement Pass 7 in these sub-passes.

Do not skip ahead if a prior sub-pass is unstable.

### Pass 7.1 — Content dedup and clustering foundation

#### Scope

Add the first real grouping layer so the system can reason about related items instead of treating every fetched item independently.

#### Implementation tasks

- define a deterministic clustering/dedup strategy for this phase
- use lightweight near-duplicate techniques first:
  - normalized URL canonicalization
  - normalized title/domain similarity
  - publication time proximity where useful
  - simple local text similarity only where needed
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
- implement local embeddings similarity scoring only if it clearly helps in this pass
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
- failures in required scoring stages are explicit and inspectable
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
  - use configured opencode provider/model settings
  - persist shortlist rationale
- define explicit failure behavior when LLM/provider fails:
  - mark the run/stage as failed
  - persist error details in run events/logs
  - do not silently downgrade to fake successful shortlist output

#### Expected output

- each run produces a defensible shortlist of items that matter most

#### Acceptance criteria

- shortlist generation works when the configured LLM path succeeds
- LLM/provider failure produces explicit failed state rather than hidden fallback output
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
  - use configured opencode provider/model settings
  - keep prompt inputs bounded and traceable
  - fail explicitly if provider/model invocation fails
- ensure scheduled daily runs can generate the same persisted report/thread/message output shape as manual runs

#### Expected output

- reports should read like actual digests rather than placeholder summaries
- source inspection from the thread UI must still work

#### Acceptance criteria

- generated reports are materially different from the current stub body
- source links in report/thread messages resolve to content items
- report/thread/message persistence remains stable
- regenerate path still works with the new report format
- failed report-generation runs are explicit and inspectable
- tests pass

---

### Pass 7.5 — Feedback-aware quality hooks

#### Scope

Use existing feedback persistence to improve traceability and prepare later tuning work without overbuilding.

#### Implementation tasks

- connect thumbs/comment/topic/source feedback into inspectable preference signals
- make sure feedback can be associated with relevant report/content context
- optionally expose lightweight influence markers in score/report generation metadata
- preserve the existing thumbs and chatbox feedback flows unchanged at the API/UI contract level
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
- explicit stage-error details when failures occur
- run-event detail that explains the major pipeline stages
- feedback context or metadata that makes downstream traceability possible without changing the current feedback UX

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
- explicit failure behavior when upstream/LLM calls fail

### API / integration tests

Add integration coverage for:

- `run-now` producing clustered/scored content
- scheduled execution producing persisted report/thread/message output
- content detail exposing useful persisted fields
- report creation from shortlisted content
- report/thread/message linkage
- regenerate behavior still working
- feedback persistence remaining stable
- scheduled and manual run failure-path behavior when required stages fail

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
- scheduled/daily execution path produces a persisted report when scheduling is enabled
- run detail shows meaningful steps and links
- content list/detail show real scores/reasons/clusters when expected
- report list/thread load successfully
- report message source inspection resolves content items
- regenerate still works if supported for the generated thread
- feedback actions still persist and read back correctly
- provider/stage failure paths show explicit run failure state and useful error detail

### Web UI QA checklist

Verify at minimum in the browser:

- workspace overview still loads
- content page loads and shows useful scoring/cluster information where exposed
- reports page loads
- report thread renders the upgraded report correctly
- source inspection panel still works
- runs page shows meaningful step timeline and generated links
- feedback page still loads and persists actions
- thumbs up/down and chatbox feedback still work on the report thread
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
- scheduled daily report generation works through the existing backend scheduler path
- required stage failures are explicit, inspectable, and never hidden behind fake success output
- regenerate still behaves correctly
- feedback persistence still works and has at least basic downstream traceability
- thumbs up/down and chatbox feedback continue to work in the report thread UX
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
- explicit failure handling throughout
- frontend contract safety throughout
- redeploy and QA before calling it complete
