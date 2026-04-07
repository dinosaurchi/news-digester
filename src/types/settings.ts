export interface WorkspaceSettings {
  id: string;
  workspaceId: string;
  schedule: {
    enabled: boolean;
    frequency: 'daily' | 'twice_daily' | 'weekly';
    timeOfDay: string;
    timezone: string;
  };
  reportStyle: 'concise' | 'detailed' | 'bulleted';
  thresholds: {
    minRelevanceScore: number;
    minFinalScore: number;
    maxArticlesPerReport: number;
  };
  retention: {
    contentDays: number;
    reportDays: number;
    runHistoryDays: number;
  };
  emailDelivery: {
    enabled: boolean;
    recipients: string[];
    subjectPrefix: string;
  };
  updatedAt?: string;
}
