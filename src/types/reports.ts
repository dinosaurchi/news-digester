export type ReportStatus = 'draft' | 'published' | 'archived';
export type MessageRole = 'system' | 'user' | 'agent';
export type FeedbackVote = 'up' | 'down';

export interface ReportThread {
  id: string;
  workspaceId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  status: ReportStatus;
  periodStart: string;
  periodEnd: string;
  runId: string;
  messageCount: number;
  latestHighlight?: string;
}

export interface ReportMessage {
  id: string;
  threadId: string;
  role: MessageRole;
  content: string;
  createdAt: string;
  feedback?: FeedbackVote;
  metadata?: {
    sources?: string[];
    reportId?: string;
    model?: string;
    tokens?: number;
  };
  isSending?: boolean;
  error?: string;
}

export interface ReportSummary {
  id: string;
  threadId: string;
  title: string;
  status: ReportStatus;
  periodStart: string;
  periodEnd: string;
  createdAt: string;
  runId: string;
  messageCount: number;
}
