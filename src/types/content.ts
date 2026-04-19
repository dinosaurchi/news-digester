export type ContentStatus = 'included' | 'excluded' | 'pending';
export type ContentType = 'news' | 'article' | 'press_release' | 'blog' | 'competitor' | 'social';

export interface ContentItem {
  id: string;
  workspaceId: string;
  title: string;
  source: string;
  sourceUrl: string;
  publisherName?: string;
  publisherDomain?: string;
  publishedAt: string;
  type: ContentType;
  relevanceScore: number;
  bm25Score: number;
  finalScore: number;
  status: ContentStatus;
  clusterId?: string;
  snippet: string;
  body?: string;
  inclusionReason?: string;
  exclusionReason?: string;
  linkedReportIds?: string[];
}

/** Theme match metadata showing which priority themes matched/unmatched. */
export interface ThemeMatch {
  matched: string[];
  unmatched: string[];
  normalized_themes?: string[];
  decomposed_themes?: Record<string, string[]>;
}

/** Competitor match metadata showing which competitors matched/unmatched. */
export interface CompetitorMatch {
  matched: string[];
  unmatched: string[];
  normalized_competitors?: string[];
  competitor_aliases?: Record<string, string[]>;
}

/** Multi-signal boost applied when multiple distinct themes match. */
export interface MultiSignalBoost {
  bonus: number;
  distinct_matched_themes: number;
}

/** User feedback details that influenced the score. */
export interface FeedbackDetails {
  topicsMatched: string[];
  sourcesMatched: string[];
  eventCount: number;
}

/**
 * Score breakdown showing individual scoring components.
 *
 * All scoring is deterministic/lexical. No LLM or semantic model is used
 * for content scoring — LLM is only used for shortlist reranking and
 * report generation.
 */
export interface ScoreBreakdown {
  relevance: number;
  bm25: number;
  freshness: number;
  sourceAuthority: number;
  feedbackAdjustment?: number;
  feedback?: FeedbackDetails;
  themeMatch?: ThemeMatch;
  competitorMatch?: CompetitorMatch;
  multiSignalBoost?: MultiSignalBoost;
  filterReason?: string;
  minRelevanceThreshold?: number;
}

export interface ContentItemDetail extends ContentItem {
  body: string;
  scoreBreakdown: ScoreBreakdown;
  clusterItems?: ContentItem[];
}
