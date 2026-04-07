import type { FeedSource } from '@/types';
import { delay, randomBetween } from './helpers';

export const MOCK_FEEDS: Record<string, FeedSource[]> = {
  'ws-1': [
    { id: 'f-1', workspaceId: 'ws-1', name: 'TechCrunch Enterprise', url: 'https://techcrunch.com/enterprise/feed', type: 'rss', status: 'healthy', lastFetchedAt: '2024-03-20T14:00:00Z', cadence: 'hourly', tags: ['tech', 'enterprise', 'startups'] },
    { id: 'f-2', workspaceId: 'ws-1', name: 'Cloud News Daily', url: 'https://cloudnews.com/feed', type: 'website', status: 'healthy', lastFetchedAt: '2024-03-20T14:00:00Z', cadence: 'daily', tags: ['cloud', 'infrastructure'] },
    { id: 'f-3', workspaceId: 'ws-1', name: 'CloudGiant Official Blog', url: 'https://cloudgiant.com/blog/feed', type: 'competitor', status: 'error', lastFetchedAt: '2024-03-19T10:00:00Z', lastError: 'HTTP 403: Access denied. Site may have blocked automated scraping.', cadence: 'daily', tags: ['competitor'] },
    { id: 'f-4', workspaceId: 'ws-1', name: 'Ars Technica AI Section', url: 'https://arstechnica.com/ai/feed', type: 'rss', status: 'healthy', lastFetchedAt: '2024-03-20T13:30:00Z', cadence: 'hourly', tags: ['ai', 'technology'] },
    { id: 'f-5', workspaceId: 'ws-1', name: 'DataNexus Press Room', url: 'https://datanexus.com/press/feed', type: 'competitor', status: 'healthy', lastFetchedAt: '2024-03-20T12:00:00Z', cadence: 'daily', tags: ['competitor'] },
    { id: 'f-6', workspaceId: 'ws-1', name: 'EU Regulatory Digest', url: 'https://euregulatorydigest.com/feed', type: 'website', status: 'healthy', lastFetchedAt: '2024-03-20T08:00:00Z', cadence: 'daily', tags: ['regulation', 'eu'] },
    { id: 'f-7', workspaceId: 'ws-1', name: 'The Verge Tech', url: 'https://theverge.com/tech/rss', type: 'rss', status: 'healthy', lastFetchedAt: '2024-03-20T14:15:00Z', cadence: 'hourly', tags: ['tech', 'consumer'] },
    { id: 'f-8', workspaceId: 'ws-1', name: 'SoftSystems Engineering Blog', url: 'https://softsystems.io/blog/feed', type: 'competitor', status: 'disabled', lastFetchedAt: '2024-03-10T09:00:00Z', cadence: 'weekly', tags: ['competitor'] },
    { id: 'f-9', workspaceId: 'ws-1', name: 'Wired Security Section', url: 'https://wired.com/security/feed', type: 'rss', status: 'healthy', lastFetchedAt: '2024-03-20T11:00:00Z', cadence: 'daily', tags: ['cybersecurity'] },
    { id: 'f-10', workspaceId: 'ws-1', name: 'NovaTech Product Updates', url: 'https://novatech.com/updates/feed', type: 'competitor', status: 'healthy', lastFetchedAt: '2024-03-20T09:30:00Z', cadence: 'daily', tags: ['competitor'] },
    { id: 'f-11', workspaceId: 'ws-1', name: 'Gartner Cloud Research', url: 'https://gartner.com/cloud/rss', type: 'website', status: 'error', lastFetchedAt: '2024-03-18T16:00:00Z', lastError: 'HTTP 429: Rate limit exceeded. Retry after 1 hour.', cadence: 'daily', tags: ['research', 'analyst'] },
    { id: 'f-12', workspaceId: 'ws-1', name: 'Kubernetes Blog', url: 'https://kubernetes.io/blog/feed', type: 'blog', status: 'healthy', lastFetchedAt: '2024-03-20T10:00:00Z', cadence: 'weekly', tags: ['cloud', 'infrastructure', 'k8s'] },
  ],
  'ws-2': [
    { id: 'f-20', workspaceId: 'ws-2', name: 'Renewable Energy World', url: 'https://renewableenergyworld.com/feed', type: 'rss', status: 'healthy', lastFetchedAt: '2024-03-19T14:00:00Z', cadence: 'daily', tags: ['renewable', 'energy'] },
    { id: 'f-21', workspaceId: 'ws-2', name: 'SolarPower World', url: 'https://solarpowerworldonline.com/feed', type: 'rss', status: 'healthy', lastFetchedAt: '2024-03-19T13:00:00Z', cadence: 'daily', tags: ['solar'] },
    { id: 'f-22', workspaceId: 'ws-2', name: 'EU Climate Policy News', url: 'https://euclimatepolicy.eu/feed', type: 'website', status: 'healthy', lastFetchedAt: '2024-03-19T08:00:00Z', cadence: 'daily', tags: ['policy', 'eu'] },
    { id: 'f-23', workspaceId: 'ws-2', name: 'SolarEdge Blog', url: 'https://solaredge.com/blog/feed', type: 'competitor', status: 'healthy', lastFetchedAt: '2024-03-19T12:00:00Z', cadence: 'weekly', tags: ['competitor'] },
    { id: 'f-24', workspaceId: 'ws-2', name: 'Energy Storage News', url: 'https://energystorage.news/feed', type: 'rss', status: 'healthy', lastFetchedAt: '2024-03-19T11:00:00Z', cadence: 'daily', tags: ['battery', 'storage'] },
    { id: 'f-25', workspaceId: 'ws-2', name: 'GreenTech Media', url: 'https://greentechmedia.com/feed', type: 'rss', status: 'error', lastFetchedAt: '2024-03-17T10:00:00Z', lastError: 'Connection timeout after 30s. Server may be down.', cadence: 'daily', tags: ['greentech'] },
  ],
  'ws-3': [
    { id: 'f-30', workspaceId: 'ws-3', name: 'Retail Dive', url: 'https://retaildive.com/feed', type: 'rss', status: 'healthy', lastFetchedAt: '2024-03-01T10:00:00Z', cadence: 'daily', tags: ['retail'] },
    { id: 'f-31', workspaceId: 'ws-3', name: 'E-commerce Times', url: 'https://ecommercetimes.com/feed', type: 'rss', status: 'healthy', lastFetchedAt: '2024-03-01T09:00:00Z', cadence: 'daily', tags: ['ecommerce'] },
    { id: 'f-32', workspaceId: 'ws-3', name: 'Supply Chain Dive', url: 'https://supplychaindive.com/feed', type: 'rss', status: 'healthy', lastFetchedAt: '2024-03-01T08:00:00Z', cadence: 'daily', tags: ['supply-chain'] },
    { id: 'f-33', workspaceId: 'ws-3', name: 'Amazon News Blog', url: 'https://amazon.com/about/news/feed', type: 'competitor', status: 'healthy', lastFetchedAt: '2024-03-01T07:00:00Z', cadence: 'daily', tags: ['competitor'] },
    { id: 'f-34', workspaceId: 'ws-3', name: 'Shopify Engineering Blog', url: 'https://shopify.com/engineering/feed', type: 'competitor', status: 'healthy', lastFetchedAt: '2024-03-01T06:00:00Z', cadence: 'weekly', tags: ['competitor'] },
    { id: 'f-35', workspaceId: 'ws-3', name: 'NRF (National Retail Federation)', url: 'https://nrf.com/news/feed', type: 'website', status: 'disabled', lastFetchedAt: '2024-02-20T10:00:00Z', cadence: 'weekly', tags: ['retail', 'industry'] },
    { id: 'f-36', workspaceId: 'ws-3', name: 'Retail Gazette UK', url: 'https://retailgazette.co.uk/feed', type: 'rss', status: 'healthy', lastFetchedAt: '2024-03-01T11:00:00Z', cadence: 'daily', tags: ['retail', 'uk'] },
    { id: 'f-37', workspaceId: 'ws-3', name: 'Modern Retail', url: 'https://modernretail.com/feed', type: 'rss', status: 'error', lastFetchedAt: '2024-02-28T15:00:00Z', lastError: 'XML parse error: Invalid feed structure.', cadence: 'daily', tags: ['retail', 'd2c'] },
  ],
  'ws-4': [
    { id: 'f-40', workspaceId: 'ws-4', name: 'Financial Times Banking', url: 'https://ft.com/banking/rss', type: 'rss', status: 'healthy', lastFetchedAt: '2024-03-20T12:00:00Z', cadence: 'hourly', tags: ['banking', 'finance'] },
    { id: 'f-41', workspaceId: 'ws-4', name: 'Fintech Futures', url: 'https://fintechfutures.com/feed', type: 'rss', status: 'healthy', lastFetchedAt: '2024-03-20T11:00:00Z', cadence: 'daily', tags: ['fintech'] },
    { id: 'f-42', workspaceId: 'ws-4', name: 'Bloomberg Finance', url: 'https://bloomberg.com/finance/rss', type: 'rss', status: 'healthy', lastFetchedAt: '2024-03-20T13:00:00Z', cadence: 'hourly', tags: ['finance', 'markets'] },
    { id: 'f-43', workspaceId: 'ws-4', name: 'Stripe Blog', url: 'https://stripe.com/blog/feed', type: 'competitor', status: 'healthy', lastFetchedAt: '2024-03-20T10:00:00Z', cadence: 'weekly', tags: ['competitor', 'payments'] },
    { id: 'f-44', workspaceId: 'ws-4', name: 'Bank for International Settlements', url: 'https://bis.org/press/rss', type: 'website', status: 'healthy', lastFetchedAt: '2024-03-20T06:00:00Z', cadence: 'daily', tags: ['regulation', 'central-banking'] },
  ],
  'ws-5': [
    { id: 'f-50', workspaceId: 'ws-5', name: 'STAT Biotech', url: 'https://statnews.com/biotech/feed', type: 'rss', status: 'healthy', lastFetchedAt: '2024-02-15T10:00:00Z', cadence: 'daily', tags: ['biotech'] },
    { id: 'f-51', workspaceId: 'ws-5', name: 'MedTech Dive', url: 'https://medtechdive.com/feed', type: 'rss', status: 'disabled', lastFetchedAt: '2024-02-10T09:00:00Z', cadence: 'daily', tags: ['medtech'] },
    { id: 'f-52', workspaceId: 'ws-5', name: 'Roche Diagnostics News', url: 'https://diagnostics.roche.com/news/feed', type: 'competitor', status: 'healthy', lastFetchedAt: '2024-02-15T08:00:00Z', cadence: 'weekly', tags: ['competitor'] },
  ],
};

export async function listFeeds(workspaceId: string): Promise<FeedSource[]> {
  await delay(randomBetween(300, 700));
  return MOCK_FEEDS[workspaceId] ? [...MOCK_FEEDS[workspaceId]] : [];
}

export async function addFeed(workspaceId: string, feed: Partial<FeedSource>): Promise<FeedSource> {
  await delay(randomBetween(500, 900));
  const newFeed: FeedSource = {
    id: `f-${Date.now().toString(36)}`,
    workspaceId,
    name: feed.name || 'New Feed',
    url: feed.url || '',
    type: feed.type || 'rss',
    status: 'healthy',
    cadence: feed.cadence || 'daily',
    tags: feed.tags || [],
  };
  if (!MOCK_FEEDS[workspaceId]) MOCK_FEEDS[workspaceId] = [];
  MOCK_FEEDS[workspaceId].push(newFeed);
  return newFeed;
}

export async function updateFeed(workspaceId: string, feedId: string, data: Partial<FeedSource>): Promise<FeedSource | undefined> {
  await delay(randomBetween(400, 800));
  const feeds = MOCK_FEEDS[workspaceId];
  if (!feeds) return undefined;
  const idx = feeds.findIndex(f => f.id === feedId);
  if (idx === -1) return undefined;
  feeds[idx] = { ...feeds[idx], ...data };
  return feeds[idx];
}

export async function toggleFeed(workspaceId: string, feedId: string): Promise<FeedSource | undefined> {
  await delay(randomBetween(300, 600));
  const feeds = MOCK_FEEDS[workspaceId];
  if (!feeds) return undefined;
  const feed = feeds.find(f => f.id === feedId);
  if (!feed) return undefined;
  feed.status = feed.status === 'disabled' ? 'healthy' : 'disabled';
  return feed;
}

export async function deleteFeed(workspaceId: string, feedId: string): Promise<boolean> {
  await delay(randomBetween(300, 600));
  const feeds = MOCK_FEEDS[workspaceId];
  if (!feeds) return false;
  const idx = feeds.findIndex(f => f.id === feedId);
  if (idx === -1) return false;
  feeds.splice(idx, 1);
  return true;
}
