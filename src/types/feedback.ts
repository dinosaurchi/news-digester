export interface FeedbackEvent {
  id: string;
  workspaceId: string;
  threadId: string;
  messageId: string;
  type: 'thumbs_up' | 'thumbs_down' | 'comment' | 'topic_preference' | 'source_preference';
  value?: string;
  createdAt: string;
  reportTitle?: string;
  messageExcerpt?: string;
}

export interface FeedbackSummary {
  totalEvents: number;
  thumbsUp: number;
  thumbsDown: number;
  topicPreferences: { topic: string; count: number; sentiment: 'positive' | 'negative' | 'neutral' }[];
  sourcePreferences: { source: string; count: number; sentiment: 'positive' | 'negative' | 'neutral' }[];
  reportStylePreferences: { style: string; count: number }[];
}
