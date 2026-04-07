import type { WorkspaceSettings } from '@/types';
import { delay, randomBetween } from './helpers';

export const MOCK_SETTINGS: Record<string, WorkspaceSettings> = {
  'ws-1': {
    id: 'settings-1',
    workspaceId: 'ws-1',
    schedule: {
      enabled: true,
      frequency: 'daily',
      timeOfDay: '08:00',
      timezone: 'America/New_York',
    },
    reportStyle: 'detailed',
    thresholds: {
      minRelevanceScore: 0.65,
      minFinalScore: 0.70,
      maxArticlesPerReport: 15,
    },
    retention: {
      contentDays: 90,
      reportDays: 365,
      runHistoryDays: 180,
    },
    emailDelivery: {
      enabled: true,
      recipients: ['cto@techcorp.com', 'strategy@techcorp.com', 'competitive-intel@techcorp.com'],
      subjectPrefix: '[TechCorp Intel]',
    },
    updatedAt: '2024-03-15T10:30:00Z',
  },
  'ws-2': {
    id: 'settings-2',
    workspaceId: 'ws-2',
    schedule: {
      enabled: true,
      frequency: 'daily',
      timeOfDay: '08:00',
      timezone: 'Europe/Berlin',
    },
    reportStyle: 'bulleted',
    thresholds: {
      minRelevanceScore: 0.60,
      minFinalScore: 0.65,
      maxArticlesPerReport: 12,
    },
    retention: {
      contentDays: 60,
      reportDays: 365,
      runHistoryDays: 90,
    },
    emailDelivery: {
      enabled: true,
      recipients: ['insights@ecosolutions.eu', 'sustainability@ecosolutions.eu'],
      subjectPrefix: '[EcoSolutions Energy Intel]',
    },
    updatedAt: '2024-03-12T14:00:00Z',
  },
  'ws-3': {
    id: 'settings-3',
    workspaceId: 'ws-3',
    schedule: {
      enabled: false,
      frequency: 'daily',
      timeOfDay: '08:00',
      timezone: 'Europe/London',
    },
    reportStyle: 'concise',
    thresholds: {
      minRelevanceScore: 0.55,
      minFinalScore: 0.60,
      maxArticlesPerReport: 20,
    },
    retention: {
      contentDays: 30,
      reportDays: 180,
      runHistoryDays: 60,
    },
    emailDelivery: {
      enabled: false,
      recipients: ['retail-intel@globalretailgroup.com'],
      subjectPrefix: '[RetailWatch]',
    },
    updatedAt: '2024-03-01T09:00:00Z',
  },
  'ws-4': {
    id: 'settings-4',
    workspaceId: 'ws-4',
    schedule: {
      enabled: true,
      frequency: 'twice_daily',
      timeOfDay: '06:00',
      timezone: 'Europe/London',
    },
    reportStyle: 'detailed',
    thresholds: {
      minRelevanceScore: 0.70,
      minFinalScore: 0.75,
      maxArticlesPerReport: 10,
    },
    retention: {
      contentDays: 120,
      reportDays: 365,
      runHistoryDays: 180,
    },
    emailDelivery: {
      enabled: true,
      recipients: ['risk@apexfinancial.com', 'compliance@apexfinancial.com'],
      subjectPrefix: '[Apex FinServ Intel]',
    },
    updatedAt: '2024-03-18T16:00:00Z',
  },
  'ws-5': {
    id: 'settings-5',
    workspaceId: 'ws-5',
    schedule: {
      enabled: false,
      frequency: 'weekly',
      timeOfDay: '08:00',
      timezone: 'America/New_York',
    },
    reportStyle: 'concise',
    thresholds: {
      minRelevanceScore: 0.50,
      minFinalScore: 0.55,
      maxArticlesPerReport: 8,
    },
    retention: {
      contentDays: 30,
      reportDays: 90,
      runHistoryDays: 30,
    },
    emailDelivery: {
      enabled: false,
      recipients: [],
      subjectPrefix: '[MediCore Intel]',
    },
    updatedAt: '2024-02-15T08:00:00Z',
  },
};

export async function getSettings(workspaceId: string): Promise<WorkspaceSettings> {
  await delay(randomBetween(300, 600));
  return MOCK_SETTINGS[workspaceId] || {
    id: `settings-${workspaceId}`,
    workspaceId,
    schedule: {
      enabled: false,
      frequency: 'daily',
      timeOfDay: '08:00',
      timezone: 'UTC',
    },
    reportStyle: 'detailed',
    thresholds: {
      minRelevanceScore: 0.65,
      minFinalScore: 0.70,
      maxArticlesPerReport: 15,
    },
    retention: {
      contentDays: 90,
      reportDays: 365,
      runHistoryDays: 180,
    },
    emailDelivery: {
      enabled: false,
      recipients: [],
      subjectPrefix: '[Intel Report]',
    },
  };
}

export async function updateSettings(workspaceId: string, data: Partial<WorkspaceSettings>): Promise<WorkspaceSettings> {
  await delay(randomBetween(500, 900));
  const existing = MOCK_SETTINGS[workspaceId] || {
    id: `settings-${workspaceId}`,
    workspaceId,
    schedule: { enabled: false, frequency: 'daily', timeOfDay: '08:00', timezone: 'UTC' },
    reportStyle: 'detailed',
    thresholds: { minRelevanceScore: 0.65, minFinalScore: 0.70, maxArticlesPerReport: 15 },
    retention: { contentDays: 90, reportDays: 365, runHistoryDays: 180 },
    emailDelivery: { enabled: false, recipients: [], subjectPrefix: '[Intel Report]' },
  };
  MOCK_SETTINGS[workspaceId] = { ...existing, ...data, updatedAt: new Date().toISOString() };
  return MOCK_SETTINGS[workspaceId];
}
