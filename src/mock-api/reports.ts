import type { ReportThread, ReportSummary } from '@/types';
import { delay, randomBetween } from './helpers';

export const MOCK_THREADS: Record<string, ReportThread[]> = {
  'ws-1': [
    {
      id: 'th-1',
      workspaceId: 'ws-1',
      title: 'Daily Intelligence Report — March 20, 2024',
      createdAt: '2024-03-20T08:00:00Z',
      updatedAt: '2024-03-20T08:05:00Z',
      status: 'published',
      periodStart: '2024-03-19T08:00:00Z',
      periodEnd: '2024-03-20T08:00:00Z',
      runId: 'run-101',
      messageCount: 3,
      latestHighlight: 'EU AI Act timeline announced — CloudGiant edge expansion — Hybrid cloud surge',
    },
    {
      id: 'th-2',
      workspaceId: 'ws-1',
      title: 'Weekly Strategic Brief — March 11–18, 2024',
      createdAt: '2024-03-18T08:00:00Z',
      updatedAt: '2024-03-18T08:10:00Z',
      status: 'published',
      periodStart: '2024-03-11T08:00:00Z',
      periodEnd: '2024-03-18T08:00:00Z',
      runId: 'run-100',
      messageCount: 1,
      latestHighlight: 'Gartner GenAI predictions — Edge computing market forecast — Kubernetes 1.30',
    },
    {
      id: 'th-3',
      workspaceId: 'ws-1',
      title: 'Competitive Alert — March 19, 2024',
      createdAt: '2024-03-19T14:00:00Z',
      updatedAt: '2024-03-19T14:30:00Z',
      status: 'published',
      periodStart: '2024-03-18T08:00:00Z',
      periodEnd: '2024-03-19T14:00:00Z',
      runId: 'run-102',
      messageCount: 3,
      latestHighlight: 'DataNexus acquisition — SoftSystems launch — CloudGiant/DataNexus partnership',
    },
    {
      id: 'th-4',
      workspaceId: 'ws-1',
      title: 'Draft Report — March 21, 2024',
      createdAt: '2024-03-21T04:00:00Z',
      updatedAt: '2024-03-21T04:02:00Z',
      status: 'draft',
      periodStart: '2024-03-20T08:00:00Z',
      periodEnd: '2024-03-21T04:00:00Z',
      runId: 'run-103',
      messageCount: 1,
    },
  ],
  'ws-2': [
    {
      id: 'th-10',
      workspaceId: 'ws-2',
      title: 'Daily Clean Energy Brief — March 19, 2024',
      createdAt: '2024-03-19T08:00:00Z',
      updatedAt: '2024-03-19T08:08:00Z',
      status: 'published',
      periodStart: '2024-03-18T08:00:00Z',
      periodEnd: '2024-03-19T08:00:00Z',
      runId: 'run-200',
      messageCount: 1,
      latestHighlight: 'EU Green Deal €3B plan — SolarEdge record revenue — Solid-state battery breakthrough',
    },
    {
      id: 'th-11',
      workspaceId: 'ws-2',
      title: 'Weekly Energy Intelligence — March 11–18, 2024',
      createdAt: '2024-03-18T08:00:00Z',
      updatedAt: '2024-03-18T08:12:00Z',
      status: 'published',
      periodStart: '2024-03-11T08:00:00Z',
      periodEnd: '2024-03-18T08:00:00Z',
      runId: 'run-201',
      messageCount: 1,
      latestHighlight: 'Tesla Berlin expansion — Smart grid APAC investment — Community solar growth',
    },
    {
      id: 'th-12',
      workspaceId: 'ws-2',
      title: 'Draft Report — March 20, 2024',
      createdAt: '2024-03-20T06:00:00Z',
      updatedAt: '2024-03-20T06:01:00Z',
      status: 'draft',
      periodStart: '2024-03-19T08:00:00Z',
      periodEnd: '2024-03-20T06:00:00Z',
      runId: 'run-202',
      messageCount: 1,
    },
  ],
  'ws-3': [
    {
      id: 'th-20',
      workspaceId: 'ws-3',
      title: 'Last Report Before Pause — March 1, 2024',
      createdAt: '2024-03-01T08:00:00Z',
      updatedAt: '2024-03-01T08:10:00Z',
      status: 'published',
      periodStart: '2024-02-28T08:00:00Z',
      periodEnd: '2024-03-01T08:00:00Z',
      runId: 'run-300',
      messageCount: 1,
      latestHighlight: 'Amazon same-day delivery expansion — E-commerce $6.3T forecast — Supply chain costs',
    },
    {
      id: 'th-21',
      workspaceId: 'ws-3',
      title: 'Earlier Retail Intelligence — Feb 28, 2024',
      createdAt: '2024-02-28T08:00:00Z',
      updatedAt: '2024-02-28T08:05:00Z',
      status: 'archived',
      periodStart: '2024-02-27T08:00:00Z',
      periodEnd: '2024-02-28T08:00:00Z',
      runId: 'run-301',
      messageCount: 1,
      latestHighlight: 'Walmart grocery tech acquisition — UK retail sales decline',
    },
  ],
  'ws-4': [
    {
      id: 'th-30',
      workspaceId: 'ws-4',
      title: 'Daily Financial Intelligence — March 20, 2024',
      createdAt: '2024-03-20T06:00:00Z',
      updatedAt: '2024-03-20T06:08:00Z',
      status: 'published',
      periodStart: '2024-03-19T06:00:00Z',
      periodEnd: '2024-03-20T06:00:00Z',
      runId: 'run-400',
      messageCount: 1,
      latestHighlight: 'PSD2 enforcement update — Stripe payment innovation — Basel IV progress',
    },
    {
      id: 'th-31',
      workspaceId: 'ws-4',
      title: 'Weekly Fintech Brief — March 11–18, 2024',
      createdAt: '2024-03-18T06:00:00Z',
      updatedAt: '2024-03-18T06:10:00Z',
      status: 'published',
      periodStart: '2024-03-11T06:00:00Z',
      periodEnd: '2024-03-18T06:00:00Z',
      runId: 'run-401',
      messageCount: 1,
      latestHighlight: 'Digital currency regulation — Open banking adoption — AML technology',
    },
  ],
  'ws-5': [
    {
      id: 'th-40',
      workspaceId: 'ws-5',
      title: 'Final Report — February 15, 2024',
      createdAt: '2024-02-15T08:00:00Z',
      updatedAt: '2024-02-15T08:05:00Z',
      status: 'archived',
      periodStart: '2024-02-14T08:00:00Z',
      periodEnd: '2024-02-15T08:00:00Z',
      runId: 'run-500',
      messageCount: 1,
      latestHighlight: 'AI diagnostics advances — Lab automation trends',
    },
  ],
};

export async function listReports(workspaceId: string): Promise<ReportThread[]> {
  await delay(randomBetween(300, 700));
  return MOCK_THREADS[workspaceId] ? [...MOCK_THREADS[workspaceId]] : [];
}

export async function getReportSummary(threadId: string): Promise<ReportSummary | undefined> {
  await delay(randomBetween(300, 600));
  for (const wsId in MOCK_THREADS) {
    const thread = MOCK_THREADS[wsId].find(t => t.id === threadId);
    if (thread) {
      return {
        id: thread.id,
        threadId: thread.id,
        title: thread.title,
        status: thread.status,
        periodStart: thread.periodStart,
        periodEnd: thread.periodEnd,
        createdAt: thread.createdAt,
        runId: thread.runId,
        messageCount: thread.messageCount,
      };
    }
  }
  return undefined;
}
