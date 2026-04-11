# OpenCode Required Handoff

**Date:** 2026-04-10  
**Recommended branch base:** current `main` / current HEAD of this repository  
**Primary target:** make OpenCode mandatory for the intelligence pipeline and report experience, with fail-fast behavior and no hidden fallback paths

---

## Why this handoff exists

The current codebase does **not** meet the desired contract.

Today:

- OpenCode is optional in backend settings via `OPENCODE_ENABLED`
- Docker Compose keeps OpenCode services behind the `opencode` profile, so `make up` does **not** start them
- shortlist refinement is optional when no OpenCode client is provided
- report generation still supports a deterministic template path when no OpenCode client is provided
- tests explicitly force `OPENCODE_ENABLED=false`

That contract is now wrong.

The required contract is:

- OpenCode is required infrastructure
- report generation must always be LLM-driven through OpenCode
- there is no deterministic report template fallback
- there is no optional disabled mode
- the system must fail fast and explicitly when OpenCode is unavailable or misconfigured
- `make up` must bring up a deployable stack that satisfies this contract

This handoff is for implementing that contract cleanly and proving it through redeploy and full-stack QA.

---

## Current baseline confirmed from repository state

These current files encode the now-obsolete optional behavior:

- `backend/app/config.py`
  - contains `OPENCODE_ENABLED: bool = False`
- `docker-compose.yml`
  - sets `OPENCODE_ENABLED`
  - keeps `opencode-server` and `opencode-agent-adapter` behind `profiles: ["opencode"]`
- `backend/app/services/pipeline.py`
  - only creates the OpenCode client when enabled
- `backend/app/services/shortlist.py`
  - accepts `opencode_client: OpenCodeClient | None`
  - allows score-only shortlist when no client is passed
- `backend/app/services/report_generator.py`
  - still supports deterministic markdown generation when no OpenCode client is passed
- `backend/app/tests/conftest.py`
  - forces `OPENCODE_ENABLED=false` for backend tests

Do not preserve any of those optional-mode semantics.

---

## Locked decisions

These decisions are fixed for this work unless explicitly superseded:

- OpenCode is mandatory for report generation
- deterministic report generation is forbidden
- OpenCode must be started by the default local deployment path
- `make up` must deploy a stack capable of the required LLM-backed behavior
- fail-fast behavior is required at config, startup, and runtime boundaries
- do not introduce silent fallback output
- do not hide failures behind score-only shortlist behavior
- do not hide failures behind template-based report generation
- do not keep a second “non-LLM mode” for local development
- if OpenCode is unavailable, the relevant operation must error clearly
- if configuration is invalid, the app should fail to start
- update tests to reflect the new contract, not the old one
- do not commit `data/`
- do not commit `.ai/tmp/`
- `make ci` must pass before completion
- completion requires `make up` redeploy and real API + Web UI QA

---

## Scope boundary

This handoff is specifically about enforcing OpenCode as a hard dependency for:

- shortlist refinement
- report generation
- report chat
- deployment/runtime contract
- tests, docs, and QA for that contract

This handoff does **not** require redesigning the existing deterministic scoring implementation unless product direction later says scoring must also become LLM-driven.

For this pass, the intended outcome is:

- deterministic scoring may remain as a preprocessing/filtering stage
- shortlist and report generation must require OpenCode
- report chat must require OpenCode
- deployment must always include the OpenCode services needed to satisfy that requirement

If leadership later decides scoring itself must also be LLM-backed, create a separate handoff after this one lands.

---

## Overall target state

After this work:

1. `make up` starts the full required stack, including OpenCode services.
2. Backend startup fails fast if OpenCode configuration is missing or invalid.
3. The pipeline does not have an “OpenCode disabled” branch.
4. Shortlist selection requires an OpenCode client.
5. Report generation requires OpenCode and never uses template fallback.
6. Report chat remains OpenCode-backed and fails explicitly when unavailable.
7. Tests no longer encode a permanent non-LLM mode as the expected path.
8. The deployed local stack can be QA’d through login, run-now, report generation, regenerate, and report-thread chat.

---

## Pass 1 - Replace the configuration contract

### Goal

Remove the optional OpenCode feature-flag model from backend configuration and make OpenCode required configuration.

### Required work

1. Remove `OPENCODE_ENABLED` from the backend settings contract.
2. Replace that toggle with explicit required configuration validation for:
   - OpenCode base URL
   - timeout
   - default model
   - default agent
   - workspace directory
3. Ensure invalid or empty required values cause startup failure, not deferred runtime ambiguity.
4. Review any env examples, docs, and bootstrapping paths that still describe OpenCode as optional.

### Files to review

- `backend/app/config.py`
- backend startup path in `backend/app/main.py`
- any env/example documentation in the repo

### Implementation notes

- Prefer failing during app startup over waiting until the first pipeline run.
- If startup validation must probe OpenCode reachability, keep that requirement explicit and deterministic.
- Do not silently substitute default non-LLM behavior.

### Pass 1 acceptance criteria

- There is no `OPENCODE_ENABLED` setting in the app configuration contract.
- Backend startup fails with a clear error if required OpenCode configuration is absent or malformed.
- Repo docs no longer describe OpenCode as optional.
- No runtime code path depends on a boolean “enabled” flag for OpenCode behavior.

---

## Pass 2 - Make deployment include OpenCode by default

### Goal

Make the default local deployment path satisfy the required OpenCode contract.

### Required work

1. Update `docker-compose.yml` so the default stack includes:
   - `opencode-server`
   - `opencode-agent-adapter`
2. Remove the profile-based gating that currently excludes those services from `make up`.
3. Ensure backend, worker, and beat all receive the required OpenCode environment values.
4. Ensure startup ordering and health checks are coherent enough for local deploys.
5. Ensure any required writable directories under `.ai/tmp/` are created or mounted correctly.

### Files to review

- `docker-compose.yml`
- any related Dockerfiles or adapter service files under `services/opencode-agent-adapter`

### Implementation notes

- `make up` should become the standard deploy path for the full required stack.
- Do not require a special profile command for the normal path.
- If OpenCode images or credentials require additional setup, document the exact local steps and fail clearly when missing.

### Pass 2 acceptance criteria

- `make up` starts OpenCode services as part of the default stack.
- `docker compose ps` shows the OpenCode services present in the default deployment.
- The backend no longer points at infrastructure that is intentionally absent from the default deployment.
- Missing OpenCode infrastructure causes an explicit deploy/startup failure, not a hidden degraded mode.

---

## Pass 3 - Make shortlist refinement mandatory

### Goal

Remove the non-LLM shortlist path as a supported system mode.

### Required work

1. Change shortlist APIs so an OpenCode client is required, not optional.
2. Remove the branch that returns a pure score-based shortlist because no client was supplied.
3. Preserve fail-fast behavior when the OpenCode call itself fails.
4. Preserve explicit logging and error propagation.

### Files to review

- `backend/app/services/shortlist.py`
- `backend/app/services/pipeline.py`

### Implementation notes

- A missing client should be treated as a programmer/configuration error.
- The existing data-matching safeguard where the LLM returns no resolvable IDs may remain only if it is still considered explicit and non-deceptive. If retained, document it clearly as a response-validation safeguard, not a disabled-mode fallback.
- Do not add any “best effort” or “continue without AI” branch.

### Pass 3 acceptance criteria

- Shortlist selection requires OpenCode at the service contract level.
- There is no branch where the pipeline intentionally skips LLM shortlist refinement because OpenCode is disabled.
- If shortlist refinement cannot run, the pipeline step fails explicitly.
- Tests reflect mandatory OpenCode-backed shortlist behavior.

---

## Pass 4 - Remove deterministic report generation completely

### Goal

Make report generation always use OpenCode and remove template fallback.

### Required work

1. Remove or make unreachable the deterministic report rendering path.
2. Require an OpenCode client in report generation service contracts.
3. Ensure regenerate also uses OpenCode-only report generation.
4. Ensure report creation, report message creation, and report metadata still behave correctly.
5. Keep fail-fast propagation when OpenCode is unavailable, times out, or returns invalid output.

### Files to review

- `backend/app/services/report_generator.py`
- `backend/app/api/reports.py`
- `backend/app/services/pipeline.py`

### Implementation notes

- This is a strict product requirement: no fallback template.
- Do not replace the template with another deterministic hidden fallback.
- Keep generated reports grounded in shortlist sources and current metadata.

### Pass 4 acceptance criteria

- Report generation cannot run without OpenCode.
- There is no deterministic template fallback path in report generation.
- Report regeneration uses the same mandatory OpenCode path.
- OpenCode failures are surfaced as explicit API/run failures.

---

## Pass 5 - Enforce fail-fast behavior at runtime boundaries

### Goal

Ensure the user sees explicit failure instead of hidden degradation whenever OpenCode is unavailable.

### Required work

1. Review all pipeline boundaries that invoke OpenCode.
2. Ensure missing dependency or infrastructure issues result in:
   - failed startup, or
   - failed request / failed pipeline step
3. Ensure API responses preserve explicit error messages and appropriate status codes.
4. Ensure run-event metadata and messages remain clear enough for operators.
5. Ensure frontend surfaces these errors rather than implying success.

### Files to review

- `backend/app/services/pipeline.py`
- `backend/app/api/reports.py`
- frontend API/client and report/runs pages under `src/`

### Implementation notes

- A pipeline that cannot refine shortlist or generate the report must not appear successful.
- A report chat request that cannot reach OpenCode must not pretend the assistant is unavailable “temporarily” if the real issue is configuration or deployment.
- Do not swallow OpenCode exceptions.

### Pass 5 acceptance criteria

- Pipeline failures caused by OpenCode appear as explicit failed steps with clear messages.
- Report chat failures return explicit non-200 API responses.
- The frontend does not mask those failures as successful output.
- No hidden fallback behavior remains for the affected OpenCode-backed features.

---

## Pass 6 - Rewrite tests for the new contract

### Goal

Make automated coverage enforce the required OpenCode contract instead of preserving the old optional mode.

### Required work

1. Remove test defaults that force `OPENCODE_ENABLED=false`.
2. Replace old assumptions with tests for:
   - startup/config validation failure when OpenCode config is invalid
   - mandatory OpenCode client requirement for shortlist/report generation
   - explicit pipeline failure when OpenCode adapter is unreachable
   - explicit report chat failure when adapter is unreachable
3. Update or replace tests that currently verify deterministic report generation or score-only shortlist as normal behavior.
4. Keep tests deterministic by mocking the OpenCode client/adapter boundary as needed.

### Files to review

- `backend/app/tests/conftest.py`
- `backend/app/tests/test_shortlist.py`
- `backend/app/tests/test_report_generator.py`
- `backend/app/tests/test_runs.py`
- `backend/app/tests/test_reports.py`
- any frontend tests touching report flows or auth/report UX assumptions

### Implementation notes

- Do not make the whole test suite depend on live external LLM infrastructure.
- Mock the OpenCode client or HTTP boundary where needed, but keep the product contract mandatory.
- The thing being tested is not “does the real provider answer”; it is “does this app require and correctly use OpenCode”.

### Pass 6 acceptance criteria

- Tests no longer encode a normal disabled-mode path.
- Tests verify explicit failure when OpenCode dependency is missing or unavailable.
- Tests verify report generation is OpenCode-only.
- `make ci` passes with the updated contract.

---

## Pass 7 - Redeploy the required stack

### Goal

Prove the updated implementation can be deployed through the normal local path and that the required OpenCode-backed services are part of that deployed stack.

### Required commands

Run all of the following successfully before handing off completion:

```bash
make ci
make up
docker compose ps
```

If startup requires additional environment variables or credentials, document the exact variables and the exact command used.

### Required work

1. Run `make up` against the updated implementation.
2. Confirm all required containers are present and running.
3. Confirm the default deployment now includes the OpenCode services needed by the contract.
4. Confirm the backend is not running in an intentionally degraded disabled mode.
5. Record the exact deploy command and env vars used.

### Pass 7 acceptance criteria

- `make up` completes successfully.
- `docker compose ps` shows the required app, backend, worker, beat, db, redis, and OpenCode services.
- The deployed stack matches the intended mandatory-OpenCode contract.
- Any missing OpenCode dependency causes explicit deploy/startup failure rather than a hidden degraded mode.

---

## Pass 8 - API QA on the deployed stack

### Goal

Prove the OpenCode-backed contract works through the deployed API, not just through tests or local code inspection.

### API QA checklist

Use the deployed stack, not test runners.

1. `GET /api/health` returns healthy status.
2. `POST /api/session/login` works with the configured admin user.
3. `GET /api/session/me` confirms authenticated session.
4. Create a fresh workspace.
5. Add at least one valid feed.
6. Trigger `POST /api/workspaces/{workspace_id}/run-now`.
7. Confirm run detail shows:
   - shortlist step completed via OpenCode path
   - report generation step completed via OpenCode path
   - no fallback/template markers
8. Confirm a report exists and report thread messages contain generated report content.
9. Call report regenerate and confirm it succeeds via OpenCode.
10. Send a report-thread chat message and confirm assistant response succeeds through OpenCode.

### Pass 8 acceptance criteria

- API QA demonstrates healthy auth, workspace, run, report, regenerate, and report-chat flows.
- The pipeline completes through OpenCode-backed shortlist and report generation paths.
- No deterministic report fallback is observed in API behavior.
- Evidence from the deployed API is recorded.

---

## Pass 9 - Web UI QA on the deployed stack

### Goal

Prove the user-facing Web UI works correctly with the new mandatory OpenCode contract.

### Web UI QA checklist

Use the browser against the deployed app at `http://localhost:3000`.

1. Log in with the configured admin user.
2. Create or open a workspace.
3. Add/test feeds from the UI.
4. Trigger `run-now` from the UI.
5. Open the run detail view and confirm the OpenCode-backed shortlist/report steps are shown as completed.
6. Open the generated report thread and verify the report content is present.
7. Trigger regenerate from the UI and verify a new generated report message appears.
8. Send a report-thread question from the UI and verify the assistant reply arrives.
9. Confirm the UI does not present a hidden non-LLM success path for report generation.

### Pass 9 acceptance criteria

- The main user flows work from the deployed Web UI.
- The run detail and report experiences reflect the mandatory OpenCode contract.
- Report regenerate and report chat work from the Web UI.
- The Web UI does not imply success when the backend has actually degraded or failed.

---

## Pass 10 - Fail-fast negative-path QA

### Goal

Prove the system fails explicitly and visibly when OpenCode is unavailable or misconfigured.

### Negative-path QA

Run at least one explicit failure-path check:

1. Temporarily break OpenCode reachability or configuration in a controlled local test.
2. Confirm the app fails fast in the expected place:
   - startup failure for invalid config, or
   - explicit 5xx / failed pipeline step for runtime dependency loss
3. Confirm there is no successful degraded report output.
4. For at least one UI-visible path, confirm the UI surfaces an explicit error instead of pretending the operation succeeded.

### Evidence to capture

Record the following in the final completion note or PR description:

- exact `make up` command used
- exact env vars required for OpenCode
- `docker compose ps` output summary
- API endpoints exercised
- Web UI flows exercised
- any failure-path scenario used to verify fail-fast behavior

### Pass 10 acceptance criteria

- At least one controlled negative-path scenario has been exercised.
- The app fails explicitly in startup or runtime as expected.
- No successful degraded report output is produced.
- The API and at least one UI-visible path surface the failure honestly.

---

## Overall acceptance criteria

The work is complete only when all of the following are true:

1. There is no `OPENCODE_ENABLED` feature flag in the runtime contract.
2. `make up` deploys the OpenCode-backed stack by default.
3. Backend startup or runtime fails explicitly when OpenCode is unavailable.
4. Shortlist refinement is mandatory and OpenCode-backed.
5. Report generation is mandatory and OpenCode-backed.
6. There is no deterministic report template fallback.
7. Report regenerate is OpenCode-backed.
8. Report chat is OpenCode-backed and explicit on failure.
9. Tests reflect the mandatory OpenCode contract and `make ci` passes.
10. `make up` redeploy is completed and verified on the deployed stack.
11. Full-stack API QA on the deployed stack demonstrates the intended behavior.
12. Full-stack Web UI QA on the deployed stack demonstrates the intended behavior.
13. Negative-path QA proves fail-fast behavior with no hidden fallback output.

---

## Known implementation risks to watch

- The current default Compose setup intentionally excludes OpenCode services; changing that may require local credential/config bootstrapping.
- Tests currently rely on forced disabled mode and will need substantial updates.
- If OpenCode service startup is slow, health checks and dependency ordering may need adjustment.
- Removing fallback paths may expose latent UI assumptions that previously only worked because degraded behavior was allowed.
- Any startup-time reachability check must avoid flaky timing behavior while still remaining fail-fast and explicit.

---

## Recommended execution order

1. Pass 1: config contract
2. Pass 2: deployment contract
3. Pass 3: mandatory shortlist
4. Pass 4: remove deterministic report generation
5. Pass 5: runtime fail-fast boundaries
6. Pass 6: tests
7. Pass 7: redeploy
8. Pass 8: API QA
9. Pass 9: Web UI QA
10. Pass 10: fail-fast negative-path QA

Do not start with UI polish. The contract change must be solved from config and deployment outward.

---

## Current verification status at handoff creation

This handoff document was written after confirming the repository still encodes the old optional contract in config, Compose, shortlist, report generation, and tests.

The implementation described here has **not** yet been completed by this document alone. The follow-on engineer must execute the passes above and then prove the result with redeploy and QA.
