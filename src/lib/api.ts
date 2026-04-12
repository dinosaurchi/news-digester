import { apiClient } from './api-client';
import type { User } from './store';
import type {
  Workspace,
  WorkspaceProfile,
  FeedSource,
  ContentItem,
  ContentItemDetail,
  ReportThread,
  ReportSummary,
  ReportMessage,
  RunSummary,
  RunDetail,
  FeedbackEvent,
  FeedbackSummary,
  WorkspaceSettings,
} from './types';
import type { ContentFilters, RunFilters } from '@/types';

// Auth
export const auth = {
  login: async (username: string, password: string): Promise<User> => {
    const res = await apiClient.post<{ user: User }>('/session/login', { username, password });
    return res.user;
  },
  me: async () => {
    const res = await apiClient.get<{ user: User }>('/session/me');
    return res.user;
  },
  logout: async () => apiClient.post('/session/logout'),
};

// Workspaces
const workspaces = {
  list: () => apiClient.get<Workspace[]>('/workspaces'),
  get: (id: string) => apiClient.get<Workspace>(`/workspaces/${id}`),
  create: (data: Partial<Workspace>) => apiClient.post<Workspace>('/workspaces', data),
  archive: (id: string) => apiClient.delete<void>(`/workspaces/${id}`),
};

// Profile
const profile = {
  get: (workspaceId: string) => apiClient.get<WorkspaceProfile>(`/workspaces/${workspaceId}/profile`),
  update: (workspaceId: string, data: Partial<WorkspaceProfile>) =>
    apiClient.put<WorkspaceProfile>(`/workspaces/${workspaceId}/profile`, data),
};

// Feeds
const feeds = {
  list: (workspaceId: string) => apiClient.get<FeedSource[]>(`/workspaces/${workspaceId}/feeds`),
  add: (workspaceId: string, feed: Partial<FeedSource>) =>
    apiClient.post<FeedSource>(`/workspaces/${workspaceId}/feeds`, feed),
  update: (workspaceId: string, feedId: string, data: Partial<FeedSource>) =>
    apiClient.patch<FeedSource>(`/feeds/${feedId}`, data),
  toggle: (workspaceId: string, feedId: string) =>
    apiClient.post<FeedSource>(`/feeds/${feedId}/toggle`),
  delete: (workspaceId: string, feedId: string) =>
    apiClient.delete<void>(`/feeds/${feedId}`).then(() => true),
};

// Content
const content = {
  list: (workspaceId: string, filters?: ContentFilters) => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([k, v]) => {
        if (v !== undefined && v !== '') params.set(k, String(v));
      });
    }
    const qs = params.toString();
    return apiClient.get<ContentItem[]>(
      `/workspaces/${workspaceId}/content${qs ? `?${qs}` : ''}`,
    );
  },
  getDetail: (workspaceId: string, contentId: string) =>
    apiClient.get<ContentItemDetail>(`/content/${contentId}`),
  getByIds: (ids: string[]) =>
    Promise.all(
      ids.map((id) => apiClient.get<ContentItem>(`/content/${id}`).catch(() => null)),
    ).then((results) => results.filter((r): r is ContentItem => r !== null)),
};

// Reports
const reports = {
  list: (workspaceId: string) => apiClient.get<ReportThread[]>(`/workspaces/${workspaceId}/reports`),
  getSummary: (threadId: string) => apiClient.get<ReportSummary>(`/reports/${threadId}`),
  getThreadMeta: (threadId: string) => apiClient.get<ReportThread>(`/report-threads/${threadId}`),
  getThread: (threadId: string) => apiClient.get<ReportThread>(`/report-threads/${threadId}`),
  getMessages: (threadId: string) =>
    apiClient.get<ReportMessage[]>(`/report-threads/${threadId}/messages`),
  sendFeedback: async (
    threadId: string,
    content: string,
  ): Promise<[ReportMessage, ReportMessage | undefined]> => {
    const res = await apiClient.post<{
      userMessage: ReportMessage;
      agentMessage?: ReportMessage;
    }>(`/report-threads/${threadId}/messages`, { content });
    return [res.userMessage, res.agentMessage ?? undefined];
  },
  vote: (messageId: string, vote: 'up' | 'down') =>
    apiClient.post<{ success: boolean }>(`/report-messages/${messageId}/thumb`, {
      value: vote,
    }),
  regenerate: (reportId: string) =>
    apiClient.post<ReportMessage>(`/reports/${reportId}/regenerate`),
};

// Runs
const runs = {
  list: (workspaceId: string, filters?: RunFilters) => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([k, v]) => {
        if (v !== undefined && v !== '') params.set(k, String(v));
      });
    }
    const qs = params.toString();
    return apiClient.get<RunSummary[]>(
      `/workspaces/${workspaceId}/runs${qs ? `?${qs}` : ''}`,
    );
  },
  getDetail: (runId: string) => apiClient.get<RunDetail>(`/runs/${runId}`),
  trigger: (workspaceId: string) => apiClient.post<RunSummary>(`/workspaces/${workspaceId}/run-now`),
};

// Feedback
const feedback = {
  list: (workspaceId: string) => apiClient.get<FeedbackEvent[]>(`/workspaces/${workspaceId}/feedback`),
  getSummary: (workspaceId: string) =>
    apiClient.get<FeedbackSummary>(`/workspaces/${workspaceId}/feedback/summary`),
};

// Settings
const settings = {
  get: (workspaceId: string) => apiClient.get<WorkspaceSettings>(`/workspaces/${workspaceId}/settings`),
  update: (workspaceId: string, data: Partial<WorkspaceSettings>) =>
    apiClient.put<WorkspaceSettings>(`/workspaces/${workspaceId}/settings`, data),
};

export const api = {
  workspaces,
  profile,
  feeds,
  content,
  reports,
  runs,
  feedback,
  settings,
};
