import type { FeedbackEvent, FeedbackSummary } from '@/types';
import { delay, randomBetween } from './helpers';

export const MOCK_FEEDBACK: Record<string, FeedbackEvent[]> = {
  'ws-1': [
    {
      id: 'fb-1', workspaceId: 'ws-1', threadId: 'th-1', messageId: 'm-1',
      type: 'thumbs_up', createdAt: '2024-03-20T08:15:00Z',
      reportTitle: 'Daily Intelligence Report — March 20, 2024',
      messageExcerpt: 'EU AI Act implementation timeline announced...',
    },
    {
      id: 'fb-2', workspaceId: 'ws-1', threadId: 'th-1', messageId: 'm-3',
      type: 'comment', value: 'Excellent analysis of the CloudGiant overlap. Can you also include pricing data?',
      createdAt: '2024-03-20T09:45:00Z',
      reportTitle: 'Daily Intelligence Report — March 20, 2024',
      messageExcerpt: 'CloudGiant Edge Expansion vs. Edge-Connect Hub Overlap...',
    },
    {
      id: 'fb-3', workspaceId: 'ws-1', threadId: 'th-2', messageId: 'm-10',
      type: 'thumbs_up', createdAt: '2024-03-18T08:20:00Z',
      reportTitle: 'Weekly Strategic Brief — March 11–18, 2024',
      messageExcerpt: 'Gartner GenAI predictions...',
    },
    {
      id: 'fb-4', workspaceId: 'ws-1', threadId: 'th-2', messageId: 'm-10',
      type: 'topic_preference', value: 'Generative AI', createdAt: '2024-03-18T08:25:00Z',
      reportTitle: 'Weekly Strategic Brief — March 11–18, 2024',
    },
    {
      id: 'fb-5', workspaceId: 'ws-1', threadId: 'th-2', messageId: 'm-10',
      type: 'topic_preference', value: 'Edge Computing', createdAt: '2024-03-18T08:25:00Z',
      reportTitle: 'Weekly Strategic Brief — March 11–18, 2024',
    },
    {
      id: 'fb-6', workspaceId: 'ws-1', threadId: 'th-3', messageId: 'm-20',
      type: 'thumbs_up', createdAt: '2024-03-19T14:10:00Z',
      reportTitle: 'Competitive Alert — March 19, 2024',
      messageExcerpt: 'Three significant competitive developments...',
    },
    {
      id: 'fb-7', workspaceId: 'ws-1', threadId: 'th-3', messageId: 'm-22',
      type: 'comment', value: 'Good assessment. Please continue monitoring SoftSystems closely.',
      createdAt: '2024-03-19T15:15:00Z',
      reportTitle: 'Competitive Alert — March 19, 2024',
      messageExcerpt: 'SoftSystems Enterprise AI Platform — Credibility Assessment...',
    },
    {
      id: 'fb-8', workspaceId: 'ws-1', threadId: 'th-1', messageId: 'm-1',
      type: 'source_preference', value: 'CloudGiant Press', createdAt: '2024-03-20T08:16:00Z',
      reportTitle: 'Daily Intelligence Report — March 20, 2024',
    },
    {
      id: 'fb-9', workspaceId: 'ws-1', threadId: 'th-1', messageId: 'm-1',
      type: 'source_preference', value: 'TechCrunch', createdAt: '2024-03-20T08:16:00Z',
      reportTitle: 'Daily Intelligence Report — March 20, 2024',
    },
    {
      id: 'fb-10', workspaceId: 'ws-1', threadId: 'th-2', messageId: 'm-10',
      type: 'thumbs_down', createdAt: '2024-03-18T09:00:00Z',
      reportTitle: 'Weekly Strategic Brief — March 11–18, 2024',
      messageExcerpt: 'NovaTech Releases Open-Source AI Orchestration Tool...',
    },
  ],
  'ws-2': [
    {
      id: 'fb-20', workspaceId: 'ws-2', threadId: 'th-10', messageId: 'm-100',
      type: 'thumbs_up', createdAt: '2024-03-19T08:15:00Z',
      reportTitle: 'Daily Clean Energy Brief — March 19, 2024',
      messageExcerpt: 'EU Green Deal Industrial Plan...',
    },
    {
      id: 'fb-21', workspaceId: 'ws-2', threadId: 'th-10', messageId: 'm-100',
      type: 'topic_preference', value: 'Battery Technology', createdAt: '2024-03-19T08:20:00Z',
      reportTitle: 'Daily Clean Energy Brief — March 19, 2024',
    },
    {
      id: 'fb-22', workspaceId: 'ws-2', threadId: 'th-10', messageId: 'm-100',
      type: 'topic_preference', value: 'Solar Energy Policy', createdAt: '2024-03-19T08:20:00Z',
      reportTitle: 'Daily Clean Energy Brief — March 19, 2024',
    },
    {
      id: 'fb-23', workspaceId: 'ws-2', threadId: 'th-11', messageId: 'm-110',
      type: 'thumbs_up', createdAt: '2024-03-18T08:20:00Z',
      reportTitle: 'Weekly Energy Intelligence — March 11–18, 2024',
      messageExcerpt: 'Tesla Energy Expands Powerwall Production...',
    },
    {
      id: 'fb-24', workspaceId: 'ws-2', threadId: 'th-11', messageId: 'm-110',
      type: 'comment', value: 'Can we get more detail on the APAC smart grid investment breakdown by country?',
      createdAt: '2024-03-18T09:00:00Z',
      reportTitle: 'Weekly Energy Intelligence — March 11–18, 2024',
    },
  ],
};

export async function listFeedback(workspaceId: string): Promise<FeedbackEvent[]> {
  await delay(randomBetween(300, 700));
  return MOCK_FEEDBACK[workspaceId] ? [...MOCK_FEEDBACK[workspaceId]] : [];
}

export async function getFeedbackSummary(workspaceId: string): Promise<FeedbackSummary> {
  await delay(randomBetween(400, 800));
  const events = MOCK_FEEDBACK[workspaceId] || [];

  const thumbsUp = events.filter(e => e.type === 'thumbs_up').length;
  const thumbsDown = events.filter(e => e.type === 'thumbs_down').length;

  const topicMap = new Map<string, { count: number; positive: number; negative: number }>();
  events.forEach(e => {
    if (e.type === 'topic_preference' && e.value) {
      const existing = topicMap.get(e.value) || { count: 0, positive: 0, negative: 0 };
      existing.count++;
      // Assume topic preferences are positive signals
      existing.positive++;
      topicMap.set(e.value, existing);
    }
  });

  const sourceMap = new Map<string, { count: number; positive: number; negative: number }>();
  events.forEach(e => {
    if (e.type === 'source_preference' && e.value) {
      const existing = sourceMap.get(e.value) || { count: 0, positive: 0, negative: 0 };
      existing.count++;
      existing.positive++;
      sourceMap.set(e.value, existing);
    }
  });

  return {
    totalEvents: events.length,
    thumbsUp,
    thumbsDown,
    topicPreferences: Array.from(topicMap.entries()).map(([topic, data]) => ({
      topic,
      count: data.count,
      sentiment: data.positive > data.negative ? 'positive' : data.negative > data.positive ? 'negative' : 'neutral',
    })),
    sourcePreferences: Array.from(sourceMap.entries()).map(([source, data]) => ({
      source,
      count: data.count,
      sentiment: data.positive > data.negative ? 'positive' : data.negative > data.positive ? 'negative' : 'neutral',
    })),
    reportStylePreferences: [
      { style: 'detailed', count: thumbsUp },
      { style: 'concise', count: thumbsDown },
    ],
  };
}
