// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import ReportThreadPage from '@/pages/ReportThreadPage';

const { mockApi } = vi.hoisted(() => ({
  mockApi: {
    reports: {
      getThreadMeta: vi.fn(),
      getMessages: vi.fn(),
      sendFeedback: vi.fn(),
      vote: vi.fn(),
      regenerate: vi.fn(),
    },
    content: {
      getByIds: vi.fn(),
    },
  },
}));

vi.mock('@/lib/api', () => ({
  api: mockApi,
}));

vi.mock('motion/react', () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  motion: {
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
      <div {...props}>{children}</div>
    ),
  },
}));

vi.mock('@/components/ui/status-badge', () => ({
  StatusBadge: ({ status }: { status: string }) => <span>{status}</span>,
}));

vi.mock('@/components/ui/markdown-renderer', () => ({
  MarkdownRenderer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock('@/components/ui/typing-indicator', () => ({
  TypingIndicator: () => <div>Typing...</div>,
}));

const reportThreadApi = mockApi;

/*
 * Keep a non-hoisted alias for readability below.
 */

const api = reportThreadApi;

/* ------------------------------------------------------------------ */
/*  Test Data Mocks                                                   */
/* ------------------------------------------------------------------ */

const messageApi = {
  reports: {
    getThreadMeta: api.reports.getThreadMeta,
    getMessages: api.reports.getMessages,
    sendFeedback: api.reports.sendFeedback,
    vote: api.reports.vote,
    regenerate: api.reports.regenerate,
  },
  content: {
    getByIds: api.content.getByIds,
  },
};

function renderThreadPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/workspaces/ws-1/reports/report-1']}>
        <Routes>
          <Route
            path="/workspaces/:workspaceId/reports/:threadId"
            element={<ReportThreadPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ReportThreadPage repaired behaviors', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    messageApi.reports.getThreadMeta.mockResolvedValue({
      id: 'report-1',
      workspaceId: 'ws-1',
      title: 'Thread Title',
      status: 'published',
      periodStart: '2024-03-20T00:00:00Z',
      periodEnd: '2024-03-21T00:00:00Z',
      runId: 'run-1',
      createdAt: '2024-03-20T00:00:00Z',
      updatedAt: '2024-03-21T00:00:00Z',
      messageCount: 4,
    });

    messageApi.reports.getMessages.mockResolvedValue([
      {
        id: 'msg-system',
        threadId: 'report-1',
        role: 'system',
        content: 'System report',
        createdAt: '2024-03-20T00:00:00Z',
        metadata: { sources: ['ci-1', 'ci-2'], reportId: 'report-1' },
      },
      {
        id: 'msg-user',
        threadId: 'report-1',
        role: 'user',
        content: 'Tell me more',
        createdAt: '2024-03-20T00:05:00Z',
      },
      {
        id: 'msg-agent-1',
        threadId: 'report-1',
        role: 'agent',
        content: 'Earlier agent response',
        createdAt: '2024-03-20T00:06:00Z',
        metadata: { sources: ['ci-1'] },
      },
      {
        id: 'msg-agent-2',
        threadId: 'report-1',
        role: 'agent',
        content: 'Latest agent response',
        createdAt: '2024-03-20T00:07:00Z',
        metadata: { sources: ['ci-2'] },
      },
    ]);

    messageApi.reports.sendFeedback.mockResolvedValue([undefined, undefined]);
    messageApi.reports.vote.mockResolvedValue({ success: true });
    messageApi.reports.regenerate.mockResolvedValue({
      id: 'msg-agent-2',
      threadId: 'report-1',
      role: 'agent',
      content: 'Regenerated content',
      createdAt: '2024-03-20T00:08:00Z',
      metadata: { regenerated: true },
    });

    messageApi.content.getByIds.mockResolvedValue([
      {
        id: 'ci-1',
        workspaceId: 'ws-1',
        title: 'Source One',
        source: 'TechCrunch',
        sourceUrl: 'https://example.com/1',
        publishedAt: '2024-03-20T00:00:00Z',
        type: 'news',
        relevanceScore: 0.8,
        bm25Score: 0.7,
        finalScore: 0.75,
        status: 'included',
        snippet: 'Snippet',
      },
      {
        id: 'ci-2',
        workspaceId: 'ws-1',
        title: 'Source Two',
        source: 'Ars Technica',
        sourceUrl: 'https://example.com/2',
        publishedAt: '2024-03-20T00:00:00Z',
        type: 'news',
        relevanceScore: 0.9,
        bm25Score: 0.8,
        finalScore: 0.85,
        status: 'included',
        snippet: 'Snippet',
      },
    ]);
  });

  afterEach(() => {
    cleanup();
  });

  it('regenerates using the thread id and only exposes one regenerate action', async () => {
    const user = userEvent.setup();

    renderThreadPage();

    await waitFor(() => {
      expect(messageApi.reports.getMessages).toHaveBeenCalledWith('report-1');
    });

    const regenerateButtons = await screen.findAllByTitle('Regenerate thread response');
    expect(regenerateButtons).toHaveLength(1);

    await user.click(regenerateButtons[0]);

    await waitFor(() => {
      expect(messageApi.reports.regenerate).toHaveBeenCalledWith('report-1');
    });
  });

  it('loads source cards using content item ids from message metadata', async () => {
    const user = userEvent.setup();

    renderThreadPage();

    await waitFor(() => {
      expect(messageApi.reports.getMessages).toHaveBeenCalledWith('report-1');
    });

    const inspectButtons = await screen.findAllByTitle('Inspect sources');
    expect(inspectButtons.length).toBeGreaterThan(0);

    await user.click(inspectButtons[0]);

    await waitFor(() => {
      expect(messageApi.content.getByIds).toHaveBeenCalledWith(['ci-1', 'ci-2']);
    });

    await waitFor(() => {
      expect(screen.getByText('Source One')).toBeTruthy();
      expect(screen.getByText('Source Two')).toBeTruthy();
    });
  });
});
