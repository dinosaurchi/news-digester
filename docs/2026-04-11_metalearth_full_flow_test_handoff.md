# Handoff — Create `tests/manual/opencode_full_flow_metalearth_real_feeds.py`

## Goal

Create a **specialized real deployed-stack full-flow manual test** for the client company **Metal Earth / Fascinations**.

This new test must **follow the same real full-flow pattern** as:

- `tests/manual/opencode_full_flow_real_feeds.py`

But adapt the scenario to the Metal Earth business so the generated report and chat interactions are relevant to the client demo.

The test must remain a **real E2E manual QA script**:
- real deployed stack
- real login
- real workspace creation
- real profile/settings configuration
- real public feed URLs
- real feed validation
- real run-now
- real report generation through OpenCode
- real report regenerate
- real report-thread chat message
- real source item resolution through content APIs

This test is intentionally **not CI**.

---

## Why this test should be Metal Earth-specific

Metal Earth sells **3D metal model kits** and has strong emphasis on **licensed models** plus categories like **aviation, architecture, and other themed collectible models**. The site shows many licensed franchises and brand categories such as Star Wars, Marvel, Batman, Harry Potter, Boeing, and others, alongside broader categories like aviation and architecture. citeturn266022search0turn266022search3turn266022search9turn266022search19

So this test should not use generic tech-news feeds like Hacker News or Planet Python.  
It should use **business-relevant feeds** so the report quality is more representative for this client demo.

---

## High-level behavior to preserve from the existing script

The new script must preserve the same overall sequence:

1. Login
2. Create a fresh workspace
3. Configure Metal Earth-specific profile/settings
4. Add and test real public RSS feeds
5. Delete feeds that fail validation
6. Require at least one successful feed
7. Trigger run-now
8. Verify run success
9. Verify report exists
10. Verify system report message has sources
11. Resolve several source IDs via `/content/{id}`
12. Regenerate the report
13. Send one report-thread chat message
14. Verify agent response exists and includes OpenCode session metadata
15. Print summary JSON and exit 0

Keep the same general coding style and helper pattern unless there is a strong reason to improve it.

---

## Non-negotiable requirements

- Must remain **fail-fast**
- Must use the **real deployed stack**, not mocks
- Must use **real public feeds**
- Must test the **real OpenCode path** for:
  - report generation
  - report-thread chat reply
- Must verify the generated report has **real source item IDs**
- Must resolve at least one source item through the real content API
- Must clearly fail with actionable error messages if any required step does not behave as expected
- Must not silently skip broken behavior

---

## File to create

Create:

- `tests/manual/opencode_full_flow_metalearth_real_feeds.py`

Do not replace the existing generic full-flow test.  
This is an additional specialized manual QA script.

---

## Implementation strategy

Reuse the structure and helper style of `opencode_full_flow_real_feeds.py`, but change:

- workspace naming
- customer name
- profile payload
- settings payload
- feed set
- verification wording
- final chat prompt wording

You may also factor out small shared helpers if doing so improves maintainability without making the manual tests harder to read.

---

## Metal Earth-specific workspace profile

Use a profile that reflects the client’s actual business context.

### Recommended profile payload
Use something close to:

- businessName: `Metal Earth`
- description:
  `Metal Earth is a 3D metal model kit brand focused on licensed pop culture models, aviation, architecture, vehicles, space, and collectible hobby products.`
- products:
  - `3D metal model kits`
  - `licensed collectible hobby kits`
  - `aviation model kits`
  - `architecture model kits`
  - `pop culture franchise model kits`
- competitors:
  - `Piececool`
  - `UGEARS`
  - `Fascinations competitors`
  - `collectible model kit brands`
- priorityThemes:
  - `licensed products`
  - `franchise entertainment`
  - `collectibles`
  - `hobby retail`
  - `model kits`
  - `aviation`
  - `architecture`
  - `space`
  - `toy industry`
  - `gift products`
  - `fandom`
- excludedTopics:
  - `cryptocurrency`
  - `enterprise SaaS`
  - `general software engineering`
  - `pure B2B cloud infrastructure`
- notes:
  Explain that the report should prioritize:
  - new licensed IP/franchise developments
  - hobby/collectibles retail signals
  - product inspiration themes relevant to Metal Earth’s categories
  - major entertainment or aerospace/architecture news that could inform future product opportunities

Do not make the profile too verbose. Keep it realistic and useful for the report pipeline.

---

## Metal Earth-specific settings

Use permissive settings so the manual test has the best chance of producing content and a report.

### Recommended settings payload
Use something close to:

- reportStyle: `detailed`
- thresholds:
  - minRelevanceScore: `0.0`
  - minFinalScore: `0.0`
  - maxArticlesPerReport: `10` or `12`
- schedule:
  - enabled: `false`
  - frequency: `daily`
  - timeOfDay: `08:00`
  - timezone: `UTC`

The manual test should still be run-driven, not schedule-driven.

---

## Feed selection strategy

This is the most important Metal Earth-specific difference.

The feeds should be **topically relevant** to Metal Earth, but also reasonably likely to parse and return items.

### Feed selection principles

Use a mix of:

1. **Google News RSS query feeds** for business-relevant topics
2. optionally one or two stable topic feeds from recognized sources if they parse reliably
3. avoid obscure feeds likely to fail

The existing script already deletes feeds that fail validation. Keep that behavior.

### Why Google News RSS is acceptable here
For this test, Google News RSS query feeds are a good fit because:
- they are public
- they can be targeted to specific Metal Earth-relevant topics
- they better reflect the type of multi-source market/news monitoring the product is supposed to do

---

## Recommended real feed set

Use a feed list tailored to Metal Earth themes.  
Prefer query-driven feeds that are likely to return recent results.

### Suggested baseline feed list

Use feeds similar to these:

1. **Licensed products / fandom / collectibles**
   - name: `Google News - licensed products collectibles`
   - url:
     `https://news.google.com/rss/search?q=licensed+products+collectibles+hobby`
   - type: `rss`
   - cadence: `daily`

2. **Model kits / hobby retail**
   - name: `Google News - model kits hobby retail`
   - url:
     `https://news.google.com/rss/search?q=model+kits+hobby+retail`
   - type: `rss`
   - cadence: `daily`

3. **Toy industry / collectibles**
   - name: `Google News - toy industry collectibles`
   - url:
     `https://news.google.com/rss/search?q=toy+industry+collectibles`
   - type: `rss`
   - cadence: `daily`

4. **Aviation / aerospace themes**
   - name: `Google News - aviation aerospace`
   - url:
     `https://news.google.com/rss/search?q=aviation+aerospace`
   - type: `rss`
   - cadence: `daily`

5. **Architecture / landmarks / destination icons**
   - name: `Google News - architecture landmarks`
   - url:
     `https://news.google.com/rss/search?q=architecture+landmarks`
   - type: `rss`
   - cadence: `daily`

6. **Entertainment franchise releases**
   - name: `Google News - entertainment franchise releases`
   - url:
     `https://news.google.com/rss/search?q=entertainment+franchise+release`
   - type: `rss`
   - cadence: `daily`

### Optional additional feeds
You may include one or two additional feeds if they validate reliably in your environment, for example:
- Star Wars / Marvel / Batman / Harry Potter release-related query feeds
- licensing industry query feeds
- collectible gift market query feeds

But do not overload the test with too many feeds.

### Important
Do **not** use overly generic tech/startup feeds in this Metal Earth-specific test.

---

## Feed reliability rules

Keep the same pattern as the existing script:

- create each feed
- call `/feeds/{feed_id}/test`
- if test fails:
  - print the reason
  - delete the failed feed from the workspace
- require at least one successful feed before run-now

This is important to preserve the robustness of the manual test.

---

## Run verification requirements

After `run-now`, verify all of the following:

1. HTTP status is success for the run-now request
2. run ID exists
3. `GET /runs/{run_id}` succeeds
4. run status is `success`
5. the run includes meaningful steps
6. `fetch_feeds` step exists
7. `fetch_feeds.metadata.feedsSucceeded >= 1`
8. `fetch_feeds.metadata.entriesImported >= 1`
9. at least one report ID is linked in run detail

Keep the same level of verification as the generic script.

---

## Report verification requirements

Once the report is identified:

1. retrieve thread messages
2. find at least one system report message
3. verify report message contains source IDs in metadata
4. verify sources list is non-empty
5. verify report content is not the “no news items were provided” empty fallback
6. resolve at least the first 1–3 source IDs via `/content/{id}`
7. fail if content items cannot be resolved

### Stronger Metal Earth-specific verification
Add one extra quality-oriented assertion:

Check that the report content includes at least one of a small set of **Metal Earth-relevant keywords** such as:
- `licensed`
- `collectible`
- `hobby`
- `model`
- `aviation`
- `architecture`
- `franchise`
- `retail`
- `entertainment`

This should be a **softly targeted assertion**, not too strict.  
The goal is to catch obviously irrelevant reports without making the test flaky.

Implementation suggestion:
- lowercase the report content
- require that at least one or two keywords from the set appear
- keep the failure message descriptive

Do not overfit the assertion.

---

## Regenerate verification

Keep the same regenerate step:

- `POST /reports/{report_id}/regenerate`
- require HTTP success
- require returned payload looks like a system message
- print the regenerated message ID

---

## Report-thread chat verification

The chat step must remain real and must test the actual OpenCode-backed reply path.

### Recommended chat prompt
Use a Metal Earth-specific prompt, such as:

`Summarize the most important opportunities or market signals for Metal Earth from this report.`

or

`Based on this report, what are the most relevant product or licensing opportunities for Metal Earth?`

### Required assertions
After posting the chat message:

- require HTTP 201
- require `agentMessage` exists
- require `agentMessage.metadata.opencodeSessionId` exists
- require agent response content is non-empty

### Optional stronger check
Assert that the agent reply contains at least one relevant term such as:
- `opportunity`
- `product`
- `licensing`
- `collectible`
- `market`
- `franchise`

Keep this optional unless it proves stable in practice.

---

## Output summary

At the end, print a JSON summary like the generic script, but include:

- workspaceId
- runId
- reportId
- successfulFeedIds
- feedNames
- reportSourceCount
- validatedSourceCount
- reportKeywordMatches
- chatAgentMessageId

This makes demo troubleshooting easier.

---

## Recommended script behavior and structure

Preserve the same simple structure:

- env vars at top:
  - `SME_BASE_URL`
  - `SME_USERNAME`
  - `SME_PASSWORD`
- `QaError`
- `ApiClient`
- `require()`
- helper(s) for summarizing steps / keyword checks if useful
- `main()`
- `if __name__ == "__main__": ...`

Keep it easy to run by hand.

---

## Environment variables

Use the same environment variables as the existing script:

- `SME_BASE_URL`
  - default `http://127.0.0.1:8000/api`
- `SME_USERNAME`
  - default `admin`
- `SME_PASSWORD`
  - default `admin`

Do not introduce new required environment variables unless absolutely necessary.

---

## Fail-fast expectations

The new script must fail immediately and clearly when:

- login fails
- workspace creation fails
- profile/settings update fails
- all feeds fail validation
- run-now fails
- run detail is not success
- no report is created
- no system report message exists
- no report sources exist
- source content cannot be resolved
- regenerate fails
- chat reply fails
- chat reply lacks OpenCode session metadata

Do not hide failures.  
Do not silently continue after critical failures.

---

## Implementation notes

### Keep the existing generic script untouched
Do not mutate `opencode_full_flow_real_feeds.py` unless a tiny shared helper extraction is clearly beneficial.

### Optional helper extraction
If it reduces duplication cleanly, you may extract a small shared helper module for:
- `ApiClient`
- `require`
- shared report/source verification helpers

But avoid over-engineering.  
Manual tests should stay easy to inspect and edit.

### Keep the script self-explanatory
A future maintainer should be able to read the file and understand:
- what it is testing
- why the feeds were chosen
- why the assertions matter for Metal Earth

---

## Suggested docstring

Use a docstring similar to:

`Manual deployed-stack full-flow QA for the Metal Earth client scenario using the mandatory OpenCode path.`

And describe that it:
1. logs in
2. creates a fresh Metal Earth-themed workspace
3. configures Metal Earth profile/settings
4. adds/tests real business-relevant RSS feeds
5. triggers run-now
6. verifies report generation with real sources
7. regenerates the report
8. sends one Metal Earth-specific report-thread chat message

---

## Test plan

After implementation, manually run the script against the deployed stack.

### Primary validation
- script exits 0
- workspace is created
- at least one feed validates
- run-now succeeds
- report exists
- report has real sources
- at least one source content item resolves
- regenerate succeeds
- chat succeeds with OpenCode session metadata

### Relevance validation
Review the generated report manually once to confirm it looks plausibly relevant to Metal Earth:
- licensed/franchise references
- hobby/collectible market signals
- aviation/architecture/entertainment relevance
- not generic tech-news nonsense

### Negative validation
Temporarily use a broken feed URL to confirm:
- feed test fails clearly
- failed feed is removed
- script still continues if other feeds succeed
- script fails if all feeds fail

---

## Acceptance criteria

The task is complete only if all of the following are true:

1. `tests/manual/opencode_full_flow_metalearth_real_feeds.py` exists
2. it follows the same real E2E pattern as the generic OpenCode full-flow test
3. it uses Metal Earth-specific profile/settings
4. it uses Metal Earth-relevant real feed sources
5. it validates feeds before relying on them
6. it exercises real run-now, report, regenerate, and report-thread chat paths
7. it resolves real source content items via content APIs
8. it fails fast with clear messages
9. it prints a useful summary JSON at the end
10. it is readable and maintainable

---

## Final instruction

Implement this as a **client-demo-oriented manual QA script**:
- realistic
- fail-fast
- easy to run
- easy to inspect
- strongly aligned with Metal Earth business relevance
- faithful to the existing `opencode_full_flow_real_feeds.py` pattern
