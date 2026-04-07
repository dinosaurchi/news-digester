import type { FeedbackEvent, FeedbackSummary } from '@/types';
import { delay, randomBetween } from './helpers';

export const MOCK_FEEDBACK: Record<string, FeedbackEvent[]> = {
  'ws-1': [
    {
      id: 'fb-1', workspaceId: 'ws-1', threadId: 'th-1', messageId: 'm-1',
      type: 'thumbs_up', sentiment: 'positive',
      createdAt: '2024-03-20T08:15:00Z',
      reportTitle: 'Daily Intelligence Report — March 20, 2024',
      messageExcerpt: 'EU AI Act implementation timeline announced. Key provisions include sector-specific compliance deadlines and a phased enforcement approach beginning in 2025.',
      influencedReportCount: 2,
    },
    {
      id: 'fb-2', workspaceId: 'ws-1', threadId: 'th-1', messageId: 'm-3',
      type: 'comment', sentiment: 'neutral',
      value: 'Excellent analysis of the CloudGiant overlap. Can you also include pricing data in future reports?',
      createdAt: '2024-03-20T09:45:00Z',
      reportTitle: 'Daily Intelligence Report — March 20, 2024',
      messageExcerpt: 'CloudGiant Edge Expansion vs. Edge-Connect Hub Overlap — Market positioning analysis reveals significant competitive convergence in the edge computing segment.',
      influencedReportCount: 1,
    },
    {
      id: 'fb-3', workspaceId: 'ws-1', threadId: 'th-1', messageId: 'm-1',
      type: 'source_preference', sentiment: 'positive', value: 'CloudGiant Press',
      createdAt: '2024-03-20T08:16:00Z',
      reportTitle: 'Daily Intelligence Report — March 20, 2024',
      influencedReportCount: 3,
    },
    {
      id: 'fb-4', workspaceId: 'ws-1', threadId: 'th-1', messageId: 'm-1',
      type: 'source_preference', sentiment: 'positive', value: 'TechCrunch',
      createdAt: '2024-03-20T08:17:00Z',
      reportTitle: 'Daily Intelligence Report — March 20, 2024',
      influencedReportCount: 2,
    },
    {
      id: 'fb-5', workspaceId: 'ws-1', threadId: 'th-4', messageId: 'm-30',
      type: 'thumbs_up', sentiment: 'positive',
      createdAt: '2024-03-19T14:30:00Z',
      reportTitle: 'Daily Intelligence Report — March 19, 2024',
      messageExcerpt: 'Regulatory landscape shift in EU digital markets. The Digital Markets Act enforcement actions signal a new era of platform accountability.',
      influencedReportCount: 1,
    },
    {
      id: 'fb-6', workspaceId: 'ws-1', threadId: 'th-3', messageId: 'm-20',
      type: 'thumbs_up', sentiment: 'positive',
      createdAt: '2024-03-19T14:10:00Z',
      reportTitle: 'Competitive Alert — March 19, 2024',
      messageExcerpt: 'Three significant competitive developments detected across the cloud infrastructure and AI platform landscape.',
      influencedReportCount: 2,
    },
    {
      id: 'fb-7', workspaceId: 'ws-1', threadId: 'th-3', messageId: 'm-22',
      type: 'comment', sentiment: 'neutral',
      value: 'Good assessment of SoftSystems. Please continue monitoring them closely — their enterprise AI pivot could be disruptive.',
      createdAt: '2024-03-19T15:15:00Z',
      reportTitle: 'Competitive Alert — March 19, 2024',
      messageExcerpt: 'SoftSystems Enterprise AI Platform — Credibility Assessment: Strong signal with 78% confidence in strategic pivot toward enterprise AI orchestration.',
    },
    {
      id: 'fb-8', workspaceId: 'ws-1', threadId: 'th-4', messageId: 'm-32',
      type: 'comment', sentiment: 'positive',
      value: 'The section on regulatory changes was very useful. More of this depth in future reports please.',
      createdAt: '2024-03-19T16:00:00Z',
      reportTitle: 'Daily Intelligence Report — March 19, 2024',
      messageExcerpt: 'EU Digital Markets Act enforcement update: Gatekeeper designations expanding to include additional cloud service providers.',
      influencedReportCount: 2,
    },
    {
      id: 'fb-9', workspaceId: 'ws-1', threadId: 'th-2', messageId: 'm-10',
      type: 'thumbs_up', sentiment: 'positive',
      createdAt: '2024-03-18T08:20:00Z',
      reportTitle: 'Weekly Strategic Brief — March 11–18, 2024',
      messageExcerpt: 'Gartner GenAI predictions and market impact analysis. Enterprise adoption projected to reach 80% by 2026.',
      influencedReportCount: 1,
    },
    {
      id: 'fb-10', workspaceId: 'ws-1', threadId: 'th-2', messageId: 'm-10',
      type: 'topic_preference', sentiment: 'positive', value: 'Generative AI',
      createdAt: '2024-03-18T08:25:00Z',
      reportTitle: 'Weekly Strategic Brief — March 11–18, 2024',
      influencedReportCount: 3,
    },
    {
      id: 'fb-11', workspaceId: 'ws-1', threadId: 'th-2', messageId: 'm-10',
      type: 'topic_preference', sentiment: 'positive', value: 'Edge Computing',
      createdAt: '2024-03-18T08:26:00Z',
      reportTitle: 'Weekly Strategic Brief — March 11–18, 2024',
      influencedReportCount: 1,
    },
    {
      id: 'fb-12', workspaceId: 'ws-1', threadId: 'th-2', messageId: 'm-15',
      type: 'thumbs_down', sentiment: 'negative',
      createdAt: '2024-03-18T09:00:00Z',
      reportTitle: 'Weekly Strategic Brief — March 11–18, 2024',
      messageExcerpt: 'NovaTech Releases Open-Source AI Orchestration Tool — Initial market reaction analysis suggests limited enterprise adoption potential.',
    },
    {
      id: 'fb-13', workspaceId: 'ws-1', threadId: 'th-2', messageId: 'm-15',
      type: 'topic_preference', sentiment: 'negative', value: 'Consumer Hardware',
      createdAt: '2024-03-18T10:00:00Z',
      reportTitle: 'Weekly Strategic Brief — March 11–18, 2024',
      influencedReportCount: 2,
    },
    {
      id: 'fb-14', workspaceId: 'ws-1', threadId: 'th-2', messageId: 'm-10',
      type: 'source_preference', sentiment: 'negative', value: 'CryptoDaily',
      createdAt: '2024-03-18T11:00:00Z',
      reportTitle: 'Weekly Strategic Brief — March 11–18, 2024',
      influencedReportCount: 1,
    },
    {
      id: 'fb-15', workspaceId: 'ws-1', threadId: 'th-5', messageId: 'm-40',
      type: 'thumbs_down', sentiment: 'negative',
      createdAt: '2024-03-17T08:00:00Z',
      reportTitle: 'Competitive Alert — March 17, 2024',
      messageExcerpt: 'Minor competitor press release with low relevance score. Limited strategic significance for current monitoring priorities.',
    },
    {
      id: 'fb-16', workspaceId: 'ws-1', threadId: 'th-6', messageId: 'm-50',
      type: 'comment', sentiment: 'negative',
      value: 'Need more depth on the supply chain analysis section. The current coverage feels superficial.',
      createdAt: '2024-03-16T09:00:00Z',
      reportTitle: 'Weekly Strategic Brief — March 4–11, 2024',
      messageExcerpt: 'Global supply chain disruptions affecting cloud infrastructure providers. Chip shortages and logistics bottlenecks continue to impact delivery timelines.',
      influencedReportCount: 1,
    },
    {
      id: 'fb-17', workspaceId: 'ws-1', threadId: 'th-6', messageId: 'm-50',
      type: 'topic_preference', sentiment: 'positive', value: 'EU Regulations',
      createdAt: '2024-03-16T09:30:00Z',
      reportTitle: 'Weekly Strategic Brief — March 4–11, 2024',
      influencedReportCount: 2,
    },
    {
      id: 'fb-18', workspaceId: 'ws-1', threadId: 'th-6', messageId: 'm-50',
      type: 'topic_preference', sentiment: 'positive', value: 'Supply Chain Intelligence',
      createdAt: '2024-03-15T10:00:00Z',
      reportTitle: 'Weekly Strategic Brief — March 4–11, 2024',
      influencedReportCount: 1,
    },
  ],
  'ws-2': [
    {
      id: 'fb-20', workspaceId: 'ws-2', threadId: 'th-10', messageId: 'm-100',
      type: 'thumbs_up', sentiment: 'positive',
      createdAt: '2024-03-19T08:15:00Z',
      reportTitle: 'Daily Clean Energy Brief — March 19, 2024',
      messageExcerpt: 'EU Green Deal Industrial Plan funding allocation update. Major investment in battery manufacturing and hydrogen infrastructure.',
      influencedReportCount: 1,
    },
    {
      id: 'fb-21', workspaceId: 'ws-2', threadId: 'th-10', messageId: 'm-100',
      type: 'topic_preference', sentiment: 'positive', value: 'Battery Technology',
      createdAt: '2024-03-19T08:20:00Z',
      reportTitle: 'Daily Clean Energy Brief — March 19, 2024',
      influencedReportCount: 2,
    },
    {
      id: 'fb-22', workspaceId: 'ws-2', threadId: 'th-10', messageId: 'm-100',
      type: 'topic_preference', sentiment: 'positive', value: 'Solar Energy Policy',
      createdAt: '2024-03-19T08:21:00Z',
      reportTitle: 'Daily Clean Energy Brief — March 19, 2024',
      influencedReportCount: 1,
    },
    {
      id: 'fb-23', workspaceId: 'ws-2', threadId: 'th-11', messageId: 'm-110',
      type: 'thumbs_up', sentiment: 'positive',
      createdAt: '2024-03-18T08:20:00Z',
      reportTitle: 'Weekly Energy Intelligence — March 11–18, 2024',
      messageExcerpt: 'Tesla Energy Expands Powerwall Production Capacity by 40%. Strategic implications for residential energy storage market.',
    },
    {
      id: 'fb-24', workspaceId: 'ws-2', threadId: 'th-11', messageId: 'm-110',
      type: 'comment', sentiment: 'neutral',
      value: 'Can we get more detail on the APAC smart grid investment breakdown by country?',
      createdAt: '2024-03-18T09:00:00Z',
      reportTitle: 'Weekly Energy Intelligence — March 11–18, 2024',
      messageExcerpt: 'APAC Smart Grid Investment Analysis: Japan, South Korea, and Australia lead regional deployment with combined $4.2B in projected spending.',
    },
  ],
};

export async function listFeedback(workspaceId: string): Promise<FeedbackEvent[]> {
  await delay(randomBetween(300, 700));
  const events = MOCK_FEEDBACK[workspaceId] ? [...MOCK_FEEDBACK[workspaceId]] : [];
  return events.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
}

export async function getFeedbackSummary(workspaceId: string): Promise<FeedbackSummary> {
  await delay(randomBetween(400, 800));
  const events = MOCK_FEEDBACK[workspaceId] || [];

  const thumbsUp = events.filter(e => e.type === 'thumbs_up').length;
  const thumbsDown = events.filter(e => e.type === 'thumbs_down').length;

  // Aggregate topic preferences
  const topicMap = new Map<string, { count: number; positive: number; negative: number }>();
  events.forEach(e => {
    if (e.type === 'topic_preference' && e.value) {
      const existing = topicMap.get(e.value) || { count: 0, positive: 0, negative: 0 };
      existing.count++;
      if (e.sentiment === 'positive') existing.positive++;
      else if (e.sentiment === 'negative') existing.negative++;
      topicMap.set(e.value, existing);
    }
  });

  // Aggregate source preferences
  const sourceMap = new Map<string, { count: number; positive: number; negative: number }>();
  events.forEach(e => {
    if (e.type === 'source_preference' && e.value) {
      const existing = sourceMap.get(e.value) || { count: 0, positive: 0, negative: 0 };
      existing.count++;
      if (e.sentiment === 'positive') existing.positive++;
      else if (e.sentiment === 'negative') existing.negative++;
      sourceMap.set(e.value, existing);
    }
  });

  const topicPreferences = Array.from(topicMap.entries())
    .map(([topic, data]) => ({
      topic,
      count: data.count,
      sentiment: data.positive > data.negative ? 'positive' as const
        : data.negative > data.positive ? 'negative' as const
        : 'neutral' as const,
    }))
    .sort((a, b) => b.count - a.count);

  const sourcePreferences = Array.from(sourceMap.entries())
    .map(([source, data]) => ({
      source,
      count: data.count,
      sentiment: data.positive > data.negative ? 'positive' as const
        : data.negative > data.positive ? 'negative' as const
        : 'neutral' as const,
    }))
    .sort((a, b) => b.count - a.count);

  return {
    totalEvents: events.length,
    thumbsUp,
    thumbsDown,
    netSentiment: thumbsUp - thumbsDown,
    topicPreferences,
    sourcePreferences,
    reportStylePreferences: [
      { style: 'detailed', count: 8 },
      { style: 'bulleted', count: 6 },
      { style: 'concise', count: 4 },
    ],
  };
}
