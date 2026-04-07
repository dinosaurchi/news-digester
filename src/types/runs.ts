export type RunType = 'scheduled' | 'manual';
export type RunStatus = 'success' | 'failed' | 'running';

export interface RunSummary {
  id: string;
  workspaceId: string;
  type: RunType;
  status: RunStatus;
  startedAt: string;
  completedAt?: string;
  durationMs?: number;
  affectedCounts: {
    feeds: number;
    articles: number;
    reports: number;
  };
  error?: string;
}

export interface RunStep {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped';
  startedAt?: string;
  completedAt?: string;
  durationMs?: number;
  details?: string;
  error?: string;
}

export interface RunDetail extends RunSummary {
  steps: RunStep[];
  logSnippets: string[];
  links: {
    reports?: string[];
    contentItems?: string[];
  };
}
