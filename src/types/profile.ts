export interface WorkspaceProfile {
  id: string;
  workspaceId: string;
  businessName: string;
  description: string;
  products: string[];
  competitors: string[];
  priorityThemes: string[];
  excludedTopics: string[];
  notes: string;
  updatedAt?: string;
}
