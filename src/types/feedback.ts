export type FeedbackEventType = 'thumbs_up' | 'thumbs_down' | 'comment' | 'topic_preference' | 'source_preference';

export interface FeedbackEvent {
  id: string;
  workspaceId: string;
  threadId: string;
  messageId: string;
  type: FeedbackEventType;
  value?: string;
  sentiment?: 'positive' | 'negative' | 'neutral';
  createdAt: string;
  reportTitle?: string;
  messageExcerpt?: string;
  influencedReportCount?: number;
}

export interface FeedbackSummary {
  totalEvents: number;
  thumbsUp: number;
  thumbsDown: number;
  netSentiment: number;
  topicPreferences: { topic: string; count: number; sentiment: 'positive' | 'negative' | 'neutral' }[];
  sourcePreferences: { source: string; count: number; sentiment: 'positive' | 'negative' | 'neutral' }[];
  reportStylePreferences: { style: string; count: number }[];
}
