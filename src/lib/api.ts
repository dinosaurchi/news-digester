// Re-export everything from the modular mock API
export * from '@/mock-api';

// Backward-compatible api object facade
import { listWorkspaces, getWorkspace, createWorkspace } from '@/mock-api/workspaces';
import { getProfile, updateProfile } from '@/mock-api/profile';
import { listFeeds, addFeed, updateFeed, toggleFeed, deleteFeed } from '@/mock-api/feeds';
import { listContent, getContentDetail, getContentItemsByIds } from '@/mock-api/content';
import { listReports, getReportSummary, getThreadMeta } from '@/mock-api/reports';
import { getMessages, sendFeedback, voteMessage, regenerateMessage } from '@/mock-api/reportThreads';import { listRuns, getRunDetail, triggerRun } from '@/mock-api/runs';
import { listFeedback, getFeedbackSummary } from '@/mock-api/feedback';
import { getSettings, updateSettings } from '@/mock-api/settings';

export const api = {
  workspaces: {
    list: listWorkspaces,
    get: getWorkspace,
    create: createWorkspace,
  },
  profile: {
    get: getProfile,
    update: updateProfile,
  },
  feeds: {
    list: listFeeds,
    add: addFeed,
    update: updateFeed,
    toggle: toggleFeed,
    delete: deleteFeed,
  },
  content: {
    list: listContent,
    getDetail: getContentDetail,
    getByIds: getContentItemsByIds,
  },
  reports: {
    list: listReports,
    getSummary: getReportSummary,
    getThreadMeta,
    getThread: getMessages,
    getMessages,
    sendFeedback,
    vote: voteMessage,
    regenerate: regenerateMessage,
  },
  runs: {
    list: listRuns,
    getDetail: getRunDetail,
    trigger: triggerRun,
  },
  feedback: {
    list: listFeedback,
    getSummary: getFeedbackSummary,
  },
  settings: {
    get: getSettings,
    update: updateSettings,
  },
};
