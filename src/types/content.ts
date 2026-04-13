export type ContentStatus = 'included' | 'excluded' | 'pending';
export type ContentType = 'news' | 'article' | 'press_release' | 'blog' | 'competitor' | 'social';

export interface ContentItem {
  id: string;
  workspaceId: string;
  title: string;
  source: string;
  sourceUrl: string;
  publishedAt: string;
  type: ContentType;
  relevanceScore: number;
  llmScore: number;
  finalScore: number;
  status: ContentStatus;
  clusterId?: string;
  snippet: string;
  body?: string;
  inclusionReason?: string;
  exclusionReason?: string;
  linkedReportIds?: string[];
}

export interface ContentItemDetail extends ContentItem {
  body: string;
  scoreBreakdown: {
    relevance: number;
    llm: number;
    freshness: number;
    sourceAuthority: number;
    feedbackAdjustment?: number;
    feedback?: {
      topicsMatched: string[];
      sourcesMatched: string[];
      eventCount: number;
    };
  };
  clusterItems?: ContentItem[];
}
