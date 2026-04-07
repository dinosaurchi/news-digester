export type WorkspaceStatus = 'active' | 'paused' | 'archived';

export interface Workspace {
  id: string;
  name: string;
  customer: string;
  status: WorkspaceStatus;
  createdAt: string;
  updatedAt: string;
  feedCount: number;
  lastReportAt?: string;
  nextRunAt?: string;
}

export interface WorkspaceSummary {
  id: string;
  name: string;
  status: WorkspaceStatus;
  feedCount: number;
  lastReportAt?: string;
  nextRunAt?: string;
}
