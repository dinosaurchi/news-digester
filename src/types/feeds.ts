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
  lastError?: string;
  cadence: 'hourly' | 'daily' | 'weekly';
  tags?: string[];
}
