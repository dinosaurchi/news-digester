import type { ContentStatus, ContentType } from './content';
import type { RunType, RunStatus } from './runs';

export interface ContentFilters {
  status?: ContentStatus;
  type?: ContentType;
  source?: string;
  minScore?: number;
  dateFrom?: string;
  dateTo?: string;
}

export interface RunFilters {
  type?: RunType;
  status?: RunStatus;
  dateFrom?: string;
  dateTo?: string;
}
