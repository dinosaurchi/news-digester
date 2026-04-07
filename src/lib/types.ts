export type WorkspaceStatus = 'active' | 'paused' | 'archived';

export interface Workspace {
  id: string;
  name: string;
  customer: string;
  status: WorkspaceStatus;
  createdAt: string;
  updatedAt: string;
  feedCount: number;
  lastReportAt?: string;
  nextRunAt?: string;
}

export interface WorkspaceProfile {
  id: string;
  workspaceId: string;
  businessName: string;
  description: string;
  products: string[];
  competitors: string[];
  priorityThemes: string[];
  excludedTopics: string[];
  notes: string;
}

export type FeedType = 'rss' | 'website' | 'competitor' | 'blog';
export type FeedStatus = 'healthy' | 'error' | 'disabled';

export interface FeedSource {
  id: string;
  workspaceId: string;
  name: string;
  url: string;
  type: FeedType;
  status: FeedStatus;
  lastFetchedAt?: string;
  cadence: 'hourly' | 'daily' | 'weekly';
}

export interface ContentItem {
  id: string;
  workspaceId: string;
  title: string;
  source: string;
  publishedAt: string;
  type: string;
  relevanceScore: number;
  llmScore: number;
  finalScore: number;
  status: 'included' | 'excluded' | 'pending';
  clusterId?: string;
  snippet: string;
  url: string;
}

export interface ReportThread {
  id: string;
  workspaceId: string;
  title: string;
  createdAt: string;
  status: 'draft' | 'published' | 'archived';
  periodStart: string;
  periodEnd: string;
  runId: string;
}

export interface ReportMessage {
  id: string;
  threadId: string;
  role: 'system' | 'user' | 'agent';
  content: string;
  createdAt: string;
  feedback?: 'up' | 'down';
  metadata?: {
    sources?: string[];
    reportId?: string;
  };
}

export interface RunSummary {
  id: string;
  workspaceId: string;
  type: 'scheduled' | 'manual';
  status: 'success' | 'failed' | 'running';
  startedAt: string;
  durationMs?: number;
  affectedCounts: {
    feeds: number;
    articles: number;
    reports: number;
  };
}

export interface WorkspaceSettings {
  schedule: string; // cron or human readable
  reportStyle: 'concise' | 'detailed' | 'bulleted';
  threshold: number;
  retentionDays: number;
}
