/* global process, setInterval, console */

import { spawn } from "node:child_process";
import fs from "node:fs";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import Fastify from "fastify";
import { z } from "zod";

const envSchema = z.object({
  PORT: z.coerce.number().int().positive().default(8080),
  LOG_LEVEL: z.string().default("info"),
  STATE_PATH: z.string().default("/adapter/data/state.json"),
  OPENCODE_BASE_URL: z.string().url(),
  OPENCODE_SERVER_PASSWORD: z.string().default("changeme"),
  OPENCODE_CONFIG_DIR: z.string().default("/opencode/config"),
  MODEL_CATALOG_OVERRIDE: z.string().default("opencode/gpt-5-nano"),
  AGENT_CATALOG_OVERRIDE: z.string().default("general"),
  SESSION_TTL_MS: z.coerce.number().int().positive().default(3_600_000), // 1 hour
  GC_INTERVAL_MS: z.coerce.number().int().positive().default(300_000),  // 5 minutes
});

const env = envSchema.parse(process.env);
const stateDir = path.dirname(env.STATE_PATH);
await mkdir(stateDir, { recursive: true });

async function loadState() {
  try {
    const raw = await readFile(env.STATE_PATH, "utf8");
    const parsed = JSON.parse(raw);
    return { sessions: parsed.sessions ?? {} };
  } catch (error) {
    if (error?.code === "ENOENT") return { sessions: {} };
    throw error;
  }
}

const state = await loadState();

async function saveState() {
  const tempPath = `${env.STATE_PATH}.${process.pid}.tmp`;
  await writeFile(tempPath, `${JSON.stringify(state, null, 2)}\n`, "utf8");
  await fs.promises.rename(tempPath, env.STATE_PATH);
}

async function reapExpiredSessions() {
  const now = Date.now();
  let reaped = 0;
  for (const [id, session] of Object.entries(state.sessions)) {
    if (session.status !== "completed" && session.status !== "failed") continue;
    const completedAt = session.completed_at
      ? new Date(session.completed_at).getTime()
      : 0;
    if (completedAt > 0 && now - completedAt > env.SESSION_TTL_MS) {
      delete state.sessions[id];
      reaped++;
    }
  }
  if (reaped > 0) {
    await saveState();
  }
  return reaped;
}

// Periodic garbage collection
setInterval(() => {
  reapExpiredSessions().catch((err) =>
    console.error("session gc failed", err),
  );
}, env.GC_INTERVAL_MS);

// Run once at startup to clean stale sessions from previous runs
reapExpiredSessions().catch(() => {});

function nowIso() {
  return new Date().toISOString();
}

function csv(value) {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function publicSession(session) {
  return {
    session_id: session.session_id,
    title: session.title,
    model: session.model,
    agent: session.agent,
    created_at: session.created_at,
    updated_at: session.updated_at,
    status: session.status,
  };
}

function collectResultText(stdout) {
  const textFragments = [];
  for (const rawLine of stdout.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) continue;
    try {
      const parsed = JSON.parse(line);
      const text = parsed?.part?.text ?? parsed?.text;
      if (typeof text === "string" && text.trim()) {
        textFragments.push(text.trim());
      }
    } catch {
      // Keep going; the CLI may write non-JSON status lines.
    }
  }
  return textFragments.length > 0 ? textFragments.join("\n") : stdout.trim();
}

async function runOpenCode(session) {
  const workspaceDir = session.workspace_dir ?? "/workspace";
  await mkdir(workspaceDir, { recursive: true });

  const args = [
    "run",
    "--attach",
    env.OPENCODE_BASE_URL,
    "--password",
    env.OPENCODE_SERVER_PASSWORD,
    "--model",
    session.model,
    "--agent",
    session.agent,
    "--format",
    "json",
    "--dir",
    workspaceDir,
    session.prompt,
  ];

  const child = spawn("opencode", args, {
    cwd: workspaceDir,
    env: {
      ...process.env,
      OPENCODE_CONFIG_DIR: env.OPENCODE_CONFIG_DIR,
      OPENCODE_SERVER_PASSWORD: env.OPENCODE_SERVER_PASSWORD,
    },
    stdio: ["ignore", "pipe", "pipe"],
  });

  let stdout = "";
  let stderr = "";
  child.stdout.on("data", (chunk) => {
    stdout += chunk.toString();
  });
  child.stderr.on("data", (chunk) => {
    stderr += chunk.toString();
  });

  child.on("error", async (error) => {
    session.status = "failed";
    session.last_error = error.message;
    session.completed_at = nowIso();
    session.updated_at = session.completed_at;
    await saveState();
  });

  child.on("close", async (code, signal) => {
    session.completed_at = nowIso();
    session.updated_at = session.completed_at;
    if (code === 0) {
      session.status = "completed";
      session.output_text = collectResultText(stdout);
      session.last_error = null;
    } else {
      session.status = "failed";
      session.last_error = `opencode run exited with ${signal ? `signal ${signal}` : `code ${code}`}: ${stderr || stdout}`.trim();
    }
    await saveState();
  });
}

const createRunSchema = z.object({
  title: z.string().min(1),
  model: z.string().min(1),
  agent: z.string().min(1),
  workspace_dir: z.string().min(1).optional(),
  prompt: z.string().min(1),
}).strict();

const app = Fastify({ logger: { level: env.LOG_LEVEL } });

app.setErrorHandler((error, request, reply) => {
  request.log.error({ err: error }, "adapter request failed");
  reply.code(error instanceof z.ZodError ? 400 : 500).send({
    error: { code: "ADAPTER_ERROR", message: error.message },
  });
});

app.get("/health", async () => ({
  healthy: true,
  adapter: { name: "sme-news-admin-opencode-agent-adapter", version: "0.1.0" },
}));

app.get("/v1/models", async () => ({ items: csv(env.MODEL_CATALOG_OVERRIDE) }));

app.get("/v1/agents", async () => ({
  items: csv(env.AGENT_CATALOG_OVERRIDE).map((id) => ({ id, name: id })),
}));

app.post("/v1/runs", async (request, reply) => {
  const input = createRunSchema.parse(request.body);
  const sessionId = `sess_${Date.now()}_${Math.random().toString(16).slice(2)}`;
  const now = nowIso();
  const session = {
    session_id: sessionId,
    title: input.title,
    model: input.model,
    agent: input.agent,
    workspace_dir: input.workspace_dir ?? "/workspace",
    prompt: input.prompt,
    status: "running",
    output_text: null,
    last_error: null,
    created_at: now,
    updated_at: now,
    completed_at: null,
  };
  state.sessions[sessionId] = session;
  await saveState();
  runOpenCode(session).catch(async (error) => {
    session.status = "failed";
    session.last_error = error.message;
    session.completed_at = nowIso();
    session.updated_at = session.completed_at;
    await saveState();
  });

  reply.code(202).send({
    accepted: true,
    session_id: sessionId,
    created_at: now,
    submitted_at: nowIso(),
  });
});

app.get("/v1/sessions/:session_id", async (request, reply) => {
  const session = state.sessions[request.params.session_id];
  if (!session) {
    reply.code(404).send({ error: { code: "SESSION_NOT_FOUND", message: "Session not found" } });
    return;
  }
  return publicSession(session);
});

app.get("/v1/sessions/:session_id/result", async (request, reply) => {
  const session = state.sessions[request.params.session_id];
  if (!session) {
    reply.code(404).send({ error: { code: "SESSION_NOT_FOUND", message: "Session not found" } });
    return;
  }
  return {
    session_id: session.session_id,
    status: session.status === "completed" ? "completed" : session.status === "failed" ? "failed" : "pending",
    output_text: session.output_text,
    completed_at: session.completed_at,
    source: session.output_text ? "cli" : "unavailable",
  };
});

app.delete("/v1/sessions/:session_id", async (request, reply) => {
  const session = state.sessions[request.params.session_id];
  if (!session) {
    reply.code(404).send({ error: { code: "SESSION_NOT_FOUND", message: "Session not found" } });
    return;
  }
  delete state.sessions[request.params.session_id];
  await saveState();
  return { deleted: true, session_id: request.params.session_id };
});

app.post("/v1/sessions/purge", async () => {
  const reaped = await reapExpiredSessions();
  return { purged: reaped, remaining: Object.keys(state.sessions).length };
});

app.get("/v1/sessions/:session_id/usage", async (request, reply) => {
  const session = state.sessions[request.params.session_id];
  if (!session) {
    reply.code(404).send({ error: { code: "SESSION_NOT_FOUND", message: "Session not found" } });
    return;
  }
  return { session_id: session.session_id, source: "unavailable" };
});

await app.listen({ port: env.PORT, host: "0.0.0.0" });
