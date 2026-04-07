import type { WorkspaceProfile } from '@/types';
import { delay, randomBetween } from './helpers';

export const MOCK_PROFILES: Record<string, WorkspaceProfile> = {
  'ws-1': {
    id: 'prof-1',
    workspaceId: 'ws-1',
    businessName: 'TechCorp Inc.',
    description: 'A leading provider of enterprise cloud solutions and AI infrastructure, serving Fortune 500 companies across 40+ countries. TechCorp specializes in hybrid cloud deployments, AI-powered data analytics, and cybersecurity solutions for the financial services and healthcare sectors.',
    products: ['CloudStack Pro', 'AI-Flow Engine', 'DataGuard Shield', 'Edge-Connect Hub'],
    competitors: ['CloudGiant', 'DataNexus Corp.', 'SoftSystems International', 'NovaTech Solutions'],
    priorityThemes: ['Generative AI', 'Hybrid Cloud Architecture', 'Cybersecurity Regulations', 'Edge Computing', 'AI Compliance'],
    excludedTopics: ['Consumer hardware', 'Gaming', 'Cryptocurrency', 'Consumer social media'],
    notes: 'Focus on enterprise adoption trends and regulatory changes in the EU (AI Act) and US markets. Pay special attention to competitive moves from CloudGiant and DataNexus.',
    updatedAt: '2024-03-18T14:30:00Z',
  },
  'ws-2': {
    id: 'prof-2',
    workspaceId: 'ws-2',
    businessName: 'EcoSolutions Ltd.',
    description: 'A European clean energy company specializing in solar panel manufacturing, battery storage systems, and smart grid technology. EcoSolutions operates across 15 European countries with a growing presence in the Asia-Pacific region.',
    products: ['SunPower Panels', 'EcoStore Battery', 'GridMind Software', 'GreenConnect IoT'],
    competitors: ['SolarEdge Technologies', 'Tesla Energy', 'Vestas Wind Systems', 'Enphase Energy'],
    priorityThemes: ['Solar Energy Policy', 'Battery Technology', 'EU Green Deal', 'Carbon Credits', 'Smart Grid Innovation'],
    excludedTopics: ['Fossil fuel investments', 'Nuclear energy debates', 'Automotive industry'],
    notes: 'Monitor EU renewable energy subsidies and policy changes. Track battery recycling regulations and supply chain developments for lithium and cobalt.',
    updatedAt: '2024-03-15T10:00:00Z',
  },
  'ws-3': {
    id: 'prof-3',
    workspaceId: 'ws-3',
    businessName: 'Global Retail Group',
    description: 'An international retail conglomerate operating 2,500+ stores across Europe, North America, and Asia. The group manages brands in fashion, electronics, home goods, and grocery retail.',
    products: ['RetailConnect POS', 'ShopAnalytics Platform', 'SupplyChain Manager'],
    competitors: ['Amazon', 'Walmart', 'Alibaba Group', 'Shopify'],
    priorityThemes: ['E-commerce Trends', 'Supply Chain Optimization', 'Consumer Behavior', 'Retail Technology', 'Omnichannel Strategy'],
    excludedTopics: ['Celebrity gossip', 'Entertainment news', 'Sports results'],
    notes: 'Workspace paused due to internal restructuring. Resume monitoring in Q2 2024.',
    updatedAt: '2024-03-01T09:00:00Z',
  },
  'ws-4': {
    id: 'prof-4',
    workspaceId: 'ws-4',
    businessName: 'Apex Financial Services',
    description: 'A multinational investment bank and financial services company headquartered in London, with operations in 30+ countries. Apex provides corporate banking, wealth management, and fintech solutions.',
    products: ['ApexTrade Platform', 'WealthPilot Advisor', 'RegTech Suite', 'PayStream'],
    competitors: ['Goldman Sachs', 'JPMorgan Chase', 'HSBC', 'Stripe'],
    priorityThemes: ['Banking Regulation', 'Fintech Innovation', 'Digital Banking', 'Open Banking', 'Anti-Money Laundering'],
    excludedTopics: ['Personal finance tips', 'Credit card promotions', 'Mortgage rates for consumers'],
    notes: 'Heavy focus on PSD2, Basel IV, and digital currency regulations. Monitor fintech startup ecosystem closely.',
    updatedAt: '2024-03-20T12:00:00Z',
  },
  'ws-5': {
    id: 'prof-5',
    workspaceId: 'ws-5',
    businessName: 'MediCore Laboratories',
    description: 'A biotech company focused on diagnostic tools, laboratory automation, and health data analytics. MediCore serves hospitals, research institutions, and pharmaceutical companies worldwide.',
    products: ['DiagnosticsAI', 'LabFlow Automation', 'HealthData Insights'],
    competitors: ['Thermo Fisher Scientific', 'Roche Diagnostics', 'Siemens Healthineers'],
    priorityThemes: ['AI in Diagnostics', 'Lab Automation', 'Healthcare Regulations', 'Precision Medicine'],
    excludedTopics: ['Fitness tracking', 'Wellness apps', 'Dietary supplements'],
    notes: 'Workspace archived after MediCore was acquired. Data retained for compliance purposes.',
    updatedAt: '2024-02-15T08:00:00Z',
  },
};

export async function getProfile(workspaceId: string): Promise<WorkspaceProfile> {
  await delay(randomBetween(300, 700));
  return MOCK_PROFILES[workspaceId] || {
    id: `prof-${Date.now().toString(36)}`,
    workspaceId,
    businessName: '',
    description: '',
    products: [],
    competitors: [],
    priorityThemes: [],
    excludedTopics: [],
    notes: '',
  };
}

export async function updateProfile(workspaceId: string, data: Partial<WorkspaceProfile>): Promise<WorkspaceProfile> {
  await delay(randomBetween(500, 900));
  const existing = MOCK_PROFILES[workspaceId] || {
    id: `prof-${workspaceId}`,
    workspaceId,
    businessName: '',
    description: '',
    products: [],
    competitors: [],
    priorityThemes: [],
    excludedTopics: [],
    notes: '',
  };
  MOCK_PROFILES[workspaceId] = { ...existing, ...data, updatedAt: new Date().toISOString() };
  return MOCK_PROFILES[workspaceId];
}
