import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppLayout } from '@/components/app-layout';
import LoginPage from '@/pages/LoginPage';
import WorkspacesPage from '@/pages/WorkspacesPage';
import WorkspaceOverviewPage from '@/pages/WorkspaceOverviewPage';
import ProfilePage from '@/pages/ProfilePage';
import FeedsPage from '@/pages/FeedsPage';
import ContentPage from '@/pages/ContentPage';
import ReportsPage from '@/pages/ReportsPage';
import ReportThreadPage from '@/pages/ReportThreadPage';
import RunsPage from '@/pages/RunsPage';
import FeedbackPage from '@/pages/FeedbackPage';
import SettingsPage from '@/pages/SettingsPage';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/',
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <Navigate to="/workspaces" replace />,
      },
      {
        path: 'workspaces',
        element: <WorkspacesPage />,
      },
      {
        path: 'workspaces/:workspaceId',
        element: <WorkspaceOverviewPage />,
      },
      {
        path: 'workspaces/:workspaceId/profile',
        element: <ProfilePage />,
      },
      {
        path: 'workspaces/:workspaceId/feeds',
        element: <FeedsPage />,
      },
      {
        path: 'workspaces/:workspaceId/content',
        element: <ContentPage />,
      },
      {
        path: 'workspaces/:workspaceId/reports',
        element: <ReportsPage />,
      },
      {
        path: 'workspaces/:workspaceId/reports/:threadId',
        element: <ReportThreadPage />,
      },
      {
        path: 'workspaces/:workspaceId/runs',
        element: <RunsPage />,
      },
      {
        path: 'workspaces/:workspaceId/feedback',
        element: <FeedbackPage />,
      },
      {
        path: 'workspaces/:workspaceId/settings',
        element: <SettingsPage />,
      },
      {
        path: 'profile',
        element: <Navigate to="/workspaces" replace />,
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/workspaces" replace />,
  },
]);
