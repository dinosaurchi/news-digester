import type { RunSummary, RunDetail, RunStep, RunType, RunStatus } from '@/types';
import { delay, randomBetween } from './helpers';

const STEP_TEMPLATES: { name: string; baseDurationMs: number }[] = [
  { name: 'Feed Discovery & Validation', baseDurationMs: 15000 },
  { name: 'Content Fetching', baseDurationMs: 120000 },
  { name: 'Content Parsing & Normalization', baseDurationMs: 30000 },
  { name: 'Relevance Scoring', baseDurationMs: 45000 },
  { name: 'LLM Analysis & Scoring', baseDurationMs: 60000 },
  { name: 'Content Filtering & Ranking', baseDurationMs: 15000 },
  { name: 'Report Generation', baseDurationMs: 45000 },
  { name: 'Report Publishing', baseDurationMs: 5000 },
];

export const MOCK_RUNS: Record<string, RunSummary[]> = {
  'ws-1': [
    {
      id: 'run-101', workspaceId: 'ws-1', type: 'scheduled', status: 'success',
      startedAt: '2024-03-20T07:55:00Z', completedAt: '2024-03-20T08:00:12Z', durationMs: 312000,
      affectedCounts: { feeds: 12, articles: 156, reports: 1 },
    },
    {
      id: 'run-102', workspaceId: 'ws-1', type: 'manual', status: 'success',
      startedAt: '2024-03-19T13:55:00Z', completedAt: '2024-03-19T13:58:45Z', durationMs: 225000,
      affectedCounts: { feeds: 12, articles: 134, reports: 1 },
    },
    {
      id: 'run-103', workspaceId: 'ws-1', type: 'scheduled', status: 'running',
      startedAt: '2024-03-21T03:58:00Z',
      affectedCounts: { feeds: 12, articles: 0, reports: 0 },
    },
    {
      id: 'run-100', workspaceId: 'ws-1', type: 'scheduled', status: 'success',
      startedAt: '2024-03-18T07:55:00Z', completedAt: '2024-03-18T07:59:30Z', durationMs: 270000,
      affectedCounts: { feeds: 12, articles: 312, reports: 1 },
    },
    {
      id: 'run-99', workspaceId: 'ws-1', type: 'scheduled', status: 'failed',
      startedAt: '2024-03-17T07:55:00Z', completedAt: '2024-03-17T07:56:12Z', durationMs: 72000,
      affectedCounts: { feeds: 12, articles: 0, reports: 0 },
      error: 'Feed fetch timeout: CloudGiant Blog and Gartner feeds exceeded 30s timeout. Partial content fetched (8/12 feeds).',
    },
    {
      id: 'run-98', workspaceId: 'ws-1', type: 'manual', status: 'success',
      startedAt: '2024-03-16T15:00:00Z', completedAt: '2024-03-16T15:04:10Z', durationMs: 250000,
      affectedCounts: { feeds: 12, articles: 145, reports: 1 },
    },
    {
      id: 'run-97', workspaceId: 'ws-1', type: 'scheduled', status: 'success',
      startedAt: '2024-03-16T07:55:00Z', completedAt: '2024-03-16T07:58:20Z', durationMs: 200000,
      affectedCounts: { feeds: 12, articles: 128, reports: 1 },
    },
    {
      id: 'run-96', workspaceId: 'ws-1', type: 'scheduled', status: 'success',
      startedAt: '2024-03-15T07:55:00Z', completedAt: '2024-03-15T07:59:45Z', durationMs: 285000,
      affectedCounts: { feeds: 12, articles: 167, reports: 1 },
    },
  ],
  'ws-2': [
    {
      id: 'run-200', workspaceId: 'ws-2', type: 'scheduled', status: 'success',
      startedAt: '2024-03-19T07:55:00Z', completedAt: '2024-03-19T07:58:00Z', durationMs: 180000,
      affectedCounts: { feeds: 8, articles: 89, reports: 1 },
    },
    {
      id: 'run-201', workspaceId: 'ws-2', type: 'scheduled', status: 'success',
      startedAt: '2024-03-18T07:55:00Z', completedAt: '2024-03-18T07:57:30Z', durationMs: 150000,
      affectedCounts: { feeds: 8, articles: 178, reports: 1 },
    },
    {
      id: 'run-202', workspaceId: 'ws-2', type: 'scheduled', status: 'success',
      startedAt: '2024-03-20T05:55:00Z', completedAt: '2024-03-20T05:57:10Z', durationMs: 130000,
      affectedCounts: { feeds: 8, articles: 72, reports: 1 },
    },
    {
      id: 'run-203', workspaceId: 'ws-2', type: 'manual', status: 'failed',
      startedAt: '2024-03-17T14:00:00Z', completedAt: '2024-03-17T14:01:30Z', durationMs: 90000,
      affectedCounts: { feeds: 5, articles: 0, reports: 0 },
      error: 'Connection timeout: GreenTech Media feed returned 503 Service Unavailable.',
    },
    {
      id: 'run-204', workspaceId: 'ws-2', type: 'scheduled', status: 'success',
      startedAt: '2024-03-17T07:55:00Z', completedAt: '2024-03-17T07:57:00Z', durationMs: 120000,
      affectedCounts: { feeds: 8, articles: 95, reports: 1 },
    },
  ],
  'ws-3': [
    {
      id: 'run-300', workspaceId: 'ws-3', type: 'scheduled', status: 'success',
      startedAt: '2024-03-01T07:55:00Z', completedAt: '2024-03-01T08:00:00Z', durationMs: 300000,
      affectedCounts: { feeds: 25, articles: 210, reports: 1 },
    },
    {
      id: 'run-301', workspaceId: 'ws-3', type: 'scheduled', status: 'success',
      startedAt: '2024-02-28T07:55:00Z', completedAt: '2024-02-28T07:59:00Z', durationMs: 240000,
      affectedCounts: { feeds: 25, articles: 185, reports: 1 },
    },
    {
      id: 'run-302', workspaceId: 'ws-3', type: 'manual', status: 'success',
      startedAt: '2024-02-27T16:00:00Z', completedAt: '2024-02-27T16:03:30Z', durationMs: 210000,
      affectedCounts: { feeds: 25, articles: 156, reports: 1 },
    },
    {
      id: 'run-303', workspaceId: 'ws-3', type: 'scheduled', status: 'failed',
      startedAt: '2024-02-27T07:55:00Z', completedAt: '2024-02-27T07:56:45Z', durationMs: 105000,
      affectedCounts: { feeds: 22, articles: 45, reports: 0 },
      error: 'XML parse error on Modern Retail feed. 3 feeds skipped due to parsing errors.',
    },
    {
      id: 'run-304', workspaceId: 'ws-3', type: 'scheduled', status: 'success',
      startedAt: '2024-02-26T07:55:00Z', completedAt: '2024-02-26T07:58:15Z', durationMs: 195000,
      affectedCounts: { feeds: 25, articles: 198, reports: 1 },
    },
    {
      id: 'run-305', workspaceId: 'ws-3', type: 'scheduled', status: 'success',
      startedAt: '2024-02-25T07:55:00Z', completedAt: '2024-02-25T07:57:00Z', durationMs: 120000,
      affectedCounts: { feeds: 25, articles: 172, reports: 1 },
    },
  ],
  'ws-4': [
    {
      id: 'run-400', workspaceId: 'ws-4', type: 'scheduled', status: 'success',
      startedAt: '2024-03-20T05:55:00Z', completedAt: '2024-03-20T05:58:00Z', durationMs: 180000,
      affectedCounts: { feeds: 10, articles: 124, reports: 1 },
    },
    {
      id: 'run-401', workspaceId: 'ws-4', type: 'scheduled', status: 'success',
      startedAt: '2024-03-18T05:55:00Z', completedAt: '2024-03-18T05:57:30Z', durationMs: 150000,
      affectedCounts: { feeds: 10, articles: 145, reports: 1 },
    },
  ],
  'ws-5': [
    {
      id: 'run-500', workspaceId: 'ws-5', type: 'scheduled', status: 'success',
      startedAt: '2024-02-15T07:55:00Z', completedAt: '2024-02-15T07:57:00Z', durationMs: 120000,
      affectedCounts: { feeds: 6, articles: 78, reports: 1 },
    },
  ],
};

function generateSteps(runId: string, runStatus: 'success' | 'failed' | 'running', _totalDurationMs?: number): RunStep[] {
  const steps: RunStep[] = [];
  const baseTime = new Date('2024-03-20T07:55:00Z');
  let elapsed = 0;

  for (let i = 0; i < STEP_TEMPLATES.length; i++) {
    const template = STEP_TEMPLATES[i];
    const stepDuration = Math.floor(template.baseDurationMs * (0.8 + Math.random() * 0.4));
    const stepStatus = runStatus === 'failed' && i === 1 ? 'failed' :
                       runStatus === 'running' && i >= 4 ? 'pending' :
                       runStatus === 'running' && i === 3 ? 'running' : 'success';

    const step: RunStep = {
      id: `${runId}-step-${i + 1}`,
      name: template.name,
      status: stepStatus,
      startedAt: new Date(baseTime.getTime() + elapsed).toISOString(),
      durationMs: stepStatus === 'success' || stepStatus === 'failed' ? stepDuration : undefined,
    };

    if (stepStatus === 'success' || stepStatus === 'failed') {
      elapsed += stepDuration;
      step.completedAt = new Date(baseTime.getTime() + elapsed).toISOString();
      if (stepStatus === 'failed') {
        step.error = i === 1 ? 'Timeout: Feed fetch exceeded 30s limit for 4 feeds' : undefined;
        break;
      }
    }

    steps.push(step);
  }

  return steps;
}

export interface RunFilters {
  type?: RunType;
  status?: RunStatus;
  dateFrom?: string;
  dateTo?: string;
}

export async function listRuns(workspaceId: string, filters?: RunFilters): Promise<RunSummary[]> {
  await delay(randomBetween(300, 700));
  let runs = MOCK_RUNS[workspaceId] ? [...MOCK_RUNS[workspaceId]] : [];
  if (filters) {
    if (filters.type) runs = runs.filter(r => r.type === filters.type);
    if (filters.status) runs = runs.filter(r => r.status === filters.status);
    if (filters.dateFrom) runs = runs.filter(r => r.startedAt >= filters.dateFrom!);
    if (filters.dateTo) runs = runs.filter(r => r.startedAt <= filters.dateTo!);
  }
  return runs;
}

export async function getRunDetail(workspaceId: string, runId: string): Promise<RunDetail | undefined> {
  await delay(randomBetween(400, 800));
  const run = MOCK_RUNS[workspaceId]?.find(r => r.id === runId);
  if (!run) return undefined;

  const steps = generateSteps(runId, run.status, run.durationMs);

  const logSnippets: string[] = [];
  if (run.status === 'success') {
    logSnippets.push(
      `[INFO] Starting intelligence cycle for workspace ${workspaceId}`,
      `[INFO] Discovered ${run.affectedCounts.feeds} active feeds`,
      `[INFO] Fetched ${run.affectedCounts.articles} articles from ${run.affectedCounts.feeds} feeds`,
      `[INFO] Relevance scoring complete: ${Math.floor(run.affectedCounts.articles * 0.15)} articles above threshold`,
      `[INFO] LLM analysis complete for ${Math.floor(run.affectedCounts.articles * 0.15)} articles`,
      `[INFO] Report generated successfully (${run.durationMs}ms total)`,
      `[INFO] Published ${run.affectedCounts.reports} report(s)`,
    );
  } else if (run.status === 'failed') {
    logSnippets.push(
      `[INFO] Starting intelligence cycle for workspace ${workspaceId}`,
      `[INFO] Discovered ${run.affectedCounts.feeds} active feeds`,
      `[ERROR] Feed fetch timeout: 4 feeds exceeded 30s limit`,
      `[ERROR] Run aborted: Insufficient content for report generation`,
      `[ERROR] ${run.error}`,
    );
  } else {
    logSnippets.push(
      `[INFO] Starting intelligence cycle for workspace ${workspaceId}`,
      `[INFO] Discovered ${run.affectedCounts.feeds} active feeds`,
      `[INFO] Fetching content from feeds...`,
      `[INFO] Content fetching in progress (60% complete)`,
    );
  }

  return {
    ...run,
    steps,
    logSnippets,
    links: {
      reports: run.status === 'success' ? [`th-${runId.replace('run-', '')}`] : undefined,
      contentItems: run.status === 'success' ? Array.from({ length: Math.min(5, run.affectedCounts.articles) }, (_, i) => `c-preview-${i + 1}`) : undefined,
    },
  };
}

export async function triggerRun(workspaceId: string): Promise<RunSummary> {
  await delay(randomBetween(1500, 2500));

  const _runCount = Object.keys(MOCK_RUNS).reduce((sum, wsId) => sum + (MOCK_RUNS[wsId]?.length || 0), 0);
  const newRun: RunSummary = {
    id: `run-manual-${Date.now().toString(36)}`,
    workspaceId,
    type: 'manual',
    status: 'running',
    startedAt: new Date().toISOString(),
    affectedCounts: { feeds: 0, articles: 0, reports: 0 },
  };

  if (!MOCK_RUNS[workspaceId]) MOCK_RUNS[workspaceId] = [];
  MOCK_RUNS[workspaceId].unshift(newRun);

  // Simulate run completion after a delay
  setTimeout(() => {
    const run = MOCK_RUNS[workspaceId]?.find(r => r.id === newRun.id);
    if (run) {
      run.status = 'success';
      run.completedAt = new Date().toISOString();
      run.durationMs = randomBetween(180000, 350000);
      run.affectedCounts = {
        feeds: randomBetween(8, 12),
        articles: randomBetween(80, 200),
        reports: 1,
      };
    }
  }, 3000);

  return newRun;
}
