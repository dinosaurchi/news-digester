import type { Workspace } from '@/types';
import { delay, randomBetween } from './helpers';

export const MOCK_WORKSPACES: Workspace[] = [
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
    customer: 'EcoSolutions Ltd.',
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
  },
  {
    id: 'ws-4',
    name: 'FinServ Monitor',
    customer: 'Apex Financial Services',
    status: 'active',
    createdAt: '2024-01-22T08:30:00Z',
    updatedAt: '2024-03-20T16:45:00Z',
    feedCount: 10,
    lastReportAt: '2024-03-20T06:00:00Z',
    nextRunAt: '2024-03-21T06:00:00Z',
  },
  {
    id: 'ws-5',
    name: 'HealthTech Radar',
    customer: 'MediCore Laboratories',
    status: 'archived',
    createdAt: '2023-09-12T11:00:00Z',
    updatedAt: '2024-02-15T09:00:00Z',
    feedCount: 6,
    lastReportAt: '2024-02-15T08:00:00Z',
  },
];

export async function listWorkspaces(): Promise<Workspace[]> {
  await delay(randomBetween(300, 800));
  return [...MOCK_WORKSPACES];
}

export async function getWorkspace(id: string): Promise<Workspace | undefined> {
  await delay(randomBetween(300, 600));
  return MOCK_WORKSPACES.find(w => w.id === id);
}

export async function createWorkspace(data: Partial<Workspace>): Promise<Workspace> {
  await delay(randomBetween(500, 1000));
  const newWs: Workspace = {
    id: `ws-${Date.now().toString(36)}`,
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
