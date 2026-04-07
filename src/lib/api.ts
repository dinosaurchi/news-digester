import { 
  Workspace, 
  WorkspaceProfile, 
  FeedSource, 
  ContentItem, 
  ReportThread, 
  ReportMessage, 
  RunSummary, 
  WorkspaceSettings 
} from './types';

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// --- Mock Data ---

const MOCK_WORKSPACES: Workspace[] = [
  {
    id: 'ws-1',
    name: 'TechCorp Strategy',
    customer: 'TechCorp Inc.',
    status: 'active',
    createdAt: '2024-01-10T10:00:00Z',
    updatedAt: '2024-03-20T15:30:00Z',
    feedCount: 12,
    lastReportAt: '2024-03-20T08:00:00Z',
    nextRunAt: '2024-03-21T08:00:00Z',
  },
  {
    id: 'ws-2',
    name: 'GreenEnergy Insights',
    customer: 'EcoSolutions',
    status: 'active',
    createdAt: '2024-02-15T09:00:00Z',
    updatedAt: '2024-03-19T11:20:00Z',
    feedCount: 8,
    lastReportAt: '2024-03-19T08:00:00Z',
    nextRunAt: '2024-03-20T08:00:00Z',
  },
  {
    id: 'ws-3',
    name: 'RetailWatch',
    customer: 'Global Retail Group',
    status: 'paused',
    createdAt: '2023-11-05T14:00:00Z',
    updatedAt: '2024-03-01T10:00:00Z',
    feedCount: 25,
    lastReportAt: '2024-03-01T08:00:00Z',
  }
];

const MOCK_PROFILES: Record<string, WorkspaceProfile> = {
  'ws-1': {
    id: 'prof-1',
    workspaceId: 'ws-1',
    businessName: 'TechCorp Inc.',
    description: 'A leading provider of enterprise cloud solutions and AI infrastructure.',
    products: ['CloudStack', 'AI-Flow', 'DataGuard'],
    competitors: ['CloudGiant', 'DataNexus', 'SoftSystems'],
    priorityThemes: ['Generative AI', 'Hybrid Cloud', 'Cybersecurity', 'Edge Computing'],
    excludedTopics: ['Consumer hardware', 'Gaming', 'Cryptocurrency'],
    notes: 'Focus on enterprise adoption and regulatory changes in the EU and US markets.'
  }
};

const MOCK_FEEDS: Record<string, FeedSource[]> = {
  'ws-1': [
    { id: 'f-1', workspaceId: 'ws-1', name: 'TechCrunch Enterprise', url: 'https://techcrunch.com/enterprise/feed', type: 'rss', status: 'healthy', lastFetchedAt: '2024-03-20T14:00:00Z', cadence: 'hourly' },
    { id: 'f-2', workspaceId: 'ws-1', name: 'Cloud News Daily', url: 'https://cloudnews.com/feed', type: 'website', status: 'healthy', lastFetchedAt: '2024-03-20T14:00:00Z', cadence: 'daily' },
    { id: 'f-3', workspaceId: 'ws-1', name: 'Competitor A Blog', url: 'https://cloudgiant.com/blog', type: 'competitor', status: 'error', lastFetchedAt: '2024-03-19T10:00:00Z', cadence: 'daily' },
  ]
};

const MOCK_CONTENT: Record<string, ContentItem[]> = {
  'ws-1': [
    {
      id: 'c-1',
      workspaceId: 'ws-1',
      title: 'New EU AI Act Regulations Finalized',
      source: 'Reuters',
      publishedAt: '2024-03-20T09:00:00Z',
      type: 'News',
      relevanceScore: 0.95,
      llmScore: 0.92,
      finalScore: 0.94,
      status: 'included',
      clusterId: 'cl-1',
      snippet: 'The European Parliament has officially approved the AI Act, setting a global benchmark for AI regulation...',
      url: 'https://reuters.com/ai-act'
    },
    {
      id: 'c-2',
      workspaceId: 'ws-1',
      title: 'CloudGiant Announces New Edge Data Centers',
      source: 'CloudGiant Press',
      publishedAt: '2024-03-20T11:30:00Z',
      type: 'Competitor',
      relevanceScore: 0.88,
      llmScore: 0.85,
      finalScore: 0.87,
      status: 'included',
      clusterId: 'cl-2',
      snippet: 'In a strategic move to bolster its edge presence, CloudGiant unveiled 10 new data center locations...',
      url: 'https://cloudgiant.com/news/edge'
    },
    {
      id: 'c-3',
      workspaceId: 'ws-1',
      title: '10 Best Gaming Laptops of 2024',
      source: 'PC Gamer',
      publishedAt: '2024-03-20T08:00:00Z',
      type: 'Article',
      relevanceScore: 0.1,
      llmScore: 0.05,
      finalScore: 0.07,
      status: 'excluded',
      snippet: 'We review the top performing gaming laptops currently on the market...',
      url: 'https://pcgamer.com/best-laptops'
    }
  ]
};

const MOCK_THREADS: Record<string, ReportThread[]> = {
  'ws-1': [
    {
      id: 'th-1',
      workspaceId: 'ws-1',
      title: 'Daily Intelligence Report - March 20, 2024',
      createdAt: '2024-03-20T08:00:00Z',
      status: 'published',
      periodStart: '2024-03-19T08:00:00Z',
      periodEnd: '2024-03-20T08:00:00Z',
      runId: 'run-123'
    }
  ]
};

const MOCK_MESSAGES: Record<string, ReportMessage[]> = {
  'th-1': [
    {
      id: 'm-1',
      threadId: 'th-1',
      role: 'system',
      content: '# Daily Intelligence Report: TechCorp Strategy\n\n## Executive Summary\nToday\'s landscape is dominated by the finalization of the **EU AI Act** and aggressive edge expansion by **CloudGiant**.\n\n## Key Developments\n\n### 1. Regulatory: EU AI Act Finalized\n- **Impact:** High\n- **Summary:** The EU has set the first comprehensive legal framework for AI. TechCorp needs to audit CloudStack compliance for high-risk categories.\n- **Sources:** [Reuters](https://reuters.com/ai-act)\n\n### 2. Competitive: CloudGiant Edge Expansion\n- **Impact:** Medium\n- **Summary:** CloudGiant is moving closer to the edge, directly competing with TechCorp\'s Edge Computing roadmap.\n- **Sources:** [CloudGiant Press](https://cloudgiant.com/news/edge)\n\n## Recommended Actions\n1. Review AI compliance documentation.\n2. Accelerate Edge-Flow beta testing.',
      createdAt: '2024-03-20T08:00:05Z',
      metadata: { sources: ['c-1', 'c-2'], reportId: 'rep-1' }
    }
  ]
};

const MOCK_RUNS: Record<string, RunSummary[]> = {
  'ws-1': [
    {
      id: 'run-123',
      workspaceId: 'ws-1',
      type: 'scheduled',
      status: 'success',
      startedAt: '2024-03-20T07:55:00Z',
      durationMs: 300000,
      affectedCounts: { feeds: 12, articles: 145, reports: 1 }
    },
    {
      id: 'run-122',
      workspaceId: 'ws-1',
      type: 'manual',
      status: 'failed',
      startedAt: '2024-03-19T15:00:00Z',
      durationMs: 45000,
      affectedCounts: { feeds: 12, articles: 0, reports: 0 }
    }
  ]
};

// --- API Service ---

export const api = {
  workspaces: {
    list: async () => {
      await delay(800);
      return MOCK_WORKSPACES;
    },
    get: async (id: string) => {
      await delay(400);
      return MOCK_WORKSPACES.find(w => w.id === id);
    },
    create: async (data: Partial<Workspace>) => {
      await delay(1000);
      const newWs: Workspace = {
        id: `ws-${Math.random().toString(36).substr(2, 9)}`,
        name: data.name || 'New Workspace',
        customer: data.customer || 'New Customer',
        status: 'active',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        feedCount: 0,
      };
      MOCK_WORKSPACES.push(newWs);
      return newWs;
    }
  },
  profile: {
    get: async (workspaceId: string) => {
      await delay(500);
      return MOCK_PROFILES[workspaceId] || {
        id: 'new-prof',
        workspaceId,
        businessName: '',
        description: '',
        products: [],
        competitors: [],
        priorityThemes: [],
        excludedTopics: [],
        notes: ''
      };
    },
    update: async (workspaceId: string, data: Partial<WorkspaceProfile>) => {
      await delay(800);
      MOCK_PROFILES[workspaceId] = { ...MOCK_PROFILES[workspaceId], ...data };
      return MOCK_PROFILES[workspaceId];
    }
  },
  feeds: {
    list: async (workspaceId: string) => {
      await delay(600);
      return MOCK_FEEDS[workspaceId] || [];
    },
    add: async (workspaceId: string, feed: Partial<FeedSource>) => {
      await delay(800);
      const newFeed: FeedSource = {
        id: `f-${Math.random().toString(36).substr(2, 9)}`,
        workspaceId,
        name: feed.name || 'New Feed',
        url: feed.url || '',
        type: feed.type || 'rss',
        status: 'healthy',
        cadence: feed.cadence || 'daily'
      };
      if (!MOCK_FEEDS[workspaceId]) MOCK_FEEDS[workspaceId] = [];
      MOCK_FEEDS[workspaceId].push(newFeed);
      return newFeed;
    }
  },
  content: {
    list: async (workspaceId: string) => {
      await delay(700);
      return MOCK_CONTENT[workspaceId] || [];
    }
  },
  reports: {
    list: async (workspaceId: string) => {
      await delay(600);
      return MOCK_THREADS[workspaceId] || [];
    },
    getThread: async (threadId: string) => {
      await delay(500);
      return MOCK_MESSAGES[threadId] || [];
    },
    sendFeedback: async (threadId: string, content: string) => {
      await delay(1200);
      const userMsg: ReportMessage = {
        id: `m-${Date.now()}`,
        threadId,
        role: 'user',
        content,
        createdAt: new Date().toISOString()
      };
      const agentMsg: ReportMessage = {
        id: `m-${Date.now() + 1}`,
        threadId,
        role: 'agent',
        content: `Acknowledged. I will adjust future reports to prioritize these aspects: "${content}". I've updated the workspace preferences accordingly.`,
        createdAt: new Date(Date.now() + 2000).toISOString()
      };
      MOCK_MESSAGES[threadId].push(userMsg, agentMsg);
      return [userMsg, agentMsg];
    },
    vote: async (messageId: string, vote: 'up' | 'down') => {
      await delay(300);
      // Find and update in mock data
      for (const threadId in MOCK_MESSAGES) {
        const msg = MOCK_MESSAGES[threadId].find(m => m.id === messageId);
        if (msg) {
          msg.feedback = vote;
          break;
        }
      }
      return true;
    }
  },
  runs: {
    list: async (workspaceId: string) => {
      await delay(600);
      return MOCK_RUNS[workspaceId] || [];
    },
    trigger: async (workspaceId: string) => {
      await delay(2000);
      return true;
    }
  }
};
