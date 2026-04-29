export type RunType = 'scheduled' | 'manual';
export type RunStatus = 'success' | 'failed' | 'running' | 'queued';

export interface FeedDetail {
  feedId: string;
  feedName: string;
  feedUrl: string;
  status: string;
  entriesCount: number;
  error?: string;
}

export interface RunStepMetadata {
  feedsSucceeded?: number;
  feedsFailed?: number;
  feedsAttempted?: number;
  entriesFetched?: number;
  entriesImported?: number;
  entriesSkipped?: number;
  feedDetails?: FeedDetail[];
}

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
    entriesImported?: number;
    entriesSkipped?: number;
    feedsSucceeded?: number;
    feedsFailed?: number;
  };
  error?: string;
}

export interface RunStep {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped' | 'completed' | 'error';
  startedAt?: string;
  completedAt?: string;
  durationMs?: number;
  details?: string;
  error?: string;
  metadata?: RunStepMetadata;
}

export interface PaginatedRunsResponse {
  items: RunSummary[];
  total: number;
  has_active_run: boolean;
}

export interface RunDetail extends RunSummary {
  steps: RunStep[];
  logSnippets: string[];
  links: {
    reports?: string[];
    contentItems?: string[];
  };
}
