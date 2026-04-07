import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useParams, Link } from 'react-router-dom';
import {
  Rss,
  FileText,
  MessageSquare,
  Clock,
  ArrowRight,
  CheckCircle2,
  XCircle,
  Play,
  ChevronRight,
  Zap,
  Loader2,
} from 'lucide-react';
import { formatDate, cn } from '@/lib/utils';
import { useAppStore } from '@/lib/store';
import { useEffect, useState } from 'react';
import { StatCardSkeleton } from '@/components/ui/loading-skeleton';
import { StatusBadge } from '@/components/ui/status-badge';

export default function WorkspaceOverviewPage() {
  const params = useParams();
  const workspaceId = params.workspaceId as string;
  const { setCurrentWorkspace } = useAppStore();
  const queryClient = useQueryClient();
  const [runToast, setRunToast] = useState<{ success: boolean; message: string } | null>(null);

  const { data: workspace, isLoading: wsLoading } = useQuery({
    queryKey: ['workspace', workspaceId],
    queryFn: () => api.workspaces.get(workspaceId),
  });

  const { data: feeds, isLoading: feedsLoading } = useQuery({
    queryKey: ['feeds', workspaceId],
    queryFn: () => api.feeds.list(workspaceId),
  });

  const { data: content, isLoading: contentLoading } = useQuery({
    queryKey: ['content', workspaceId],
    queryFn: () => api.content.list(workspaceId),
  });

  const { data: runs, isLoading: runsLoading } = useQuery({
    queryKey: ['runs', workspaceId],
    queryFn: () => api.runs.list(workspaceId),
  });

  const { data: reports, isLoading: reportsLoading } = useQuery({
    queryKey: ['reports', workspaceId],
    queryFn: () => api.reports.list(workspaceId),
  });

  useEffect(() => {
    if (workspace) setCurrentWorkspace(workspace);
  }, [workspace, setCurrentWorkspace]);

  useEffect(() => {
    if (runToast) {
      const timer = setTimeout(() => setRunToast(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [runToast]);

  // Derived stats
  const healthyFeeds = feeds?.filter((f) => f.status === 'healthy').length || 0;
  const errorFeeds = feeds?.filter((f) => f.status === 'error').length || 0;
  const includedContent = content?.filter((c) => c.status === 'included').length || 0;
  const excludedContent = content?.filter((c) => c.status === 'excluded').length || 0;
  const pendingContent = content?.filter((c) => c.status === 'pending').length || 0;
  const activeReports = reports?.filter((r) => r.status === 'published').length || 0;
  const lastRun = runs?.[0];

  const runMutation = useMutation({
    mutationFn: () => api.runs.trigger(workspaceId),
    onSuccess: () => {
      setRunToast({ success: true, message: 'Intelligence cycle triggered successfully.' });
      queryClient.invalidateQueries({ queryKey: ['runs', workspaceId] });
    },
    onError: () => {
      setRunToast({ success: false, message: 'Failed to trigger run. Please try again.' });
    },
  });

  const isLoading = wsLoading || feedsLoading || contentLoading || runsLoading || reportsLoading;

  if (isLoading) {
    return (
      <div className="space-y-8">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <StatCardSkeleton key={i} />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <div className="h-64 bg-white border border-slate-200 rounded-xl animate-pulse" />
          </div>
          <div className="space-y-6">
            <div className="h-40 bg-white border border-slate-200 rounded-xl animate-pulse" />
            <div className="h-64 bg-white border border-slate-200 rounded-xl animate-pulse" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <OverviewStatCard
          title="Total Feeds"
          value={feeds?.length || 0}
          subtitle={`${healthyFeeds} healthy, ${errorFeeds} error`}
          icon={Rss}
          color="text-indigo-600"
          bg="bg-indigo-50"
        />
        <OverviewStatCard
          title="Content Items"
          value={content?.length || 0}
          subtitle={`${includedContent} included, ${excludedContent} excluded`}
          icon={FileText}
          color="text-violet-600"
          bg="bg-violet-50"
        />
        <OverviewStatCard
          title="Active Reports"
          value={activeReports}
          subtitle={`${reports?.length || 0} total`}
          icon={MessageSquare}
          color="text-amber-600"
          bg="bg-amber-50"
        />
        <OverviewStatCard
          title="Last Run"
          value={lastRun ? formatStatus(lastRun.status) : 'Never'}
          subtitle={
            lastRun?.durationMs
              ? `${Math.round(lastRun.durationMs / 1000)}s duration`
              : lastRun
                ? 'In progress...'
                : 'No runs yet'
          }
          icon={lastRun?.status === 'success' ? CheckCircle2 : lastRun?.status === 'failed' ? XCircle : Zap}
          color={
            lastRun?.status === 'success'
              ? 'text-emerald-600'
              : lastRun?.status === 'failed'
                ? 'text-red-600'
                : 'text-blue-600'
          }
          bg={
            lastRun?.status === 'success'
              ? 'bg-emerald-50'
              : lastRun?.status === 'failed'
                ? 'bg-red-50'
                : 'bg-blue-50'
          }
        />
        <OverviewStatCard
          title="Next Scheduled Run"
          value={workspace?.nextRunAt ? formatRelativeDate(workspace.nextRunAt) : 'Manual'}
          subtitle={
            workspace?.nextRunAt
              ? formatDate(workspace.nextRunAt)
              : 'Trigger manually'
          }
          icon={Clock}
          color="text-slate-600"
          bg="bg-slate-100"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Runs */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-slate-900">Recent Runs</h3>
            <Link
              to={`/workspaces/${workspaceId}/runs`}
              className="text-sm text-indigo-600 font-medium hover:underline flex items-center gap-1"
            >
              View all <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            {runs && runs.length > 0 ? (
              <div className="divide-y divide-slate-100">
                {runs.slice(0, 5).map((run) => (
                  <div key={run.id} className="flex items-center justify-between px-5 py-3.5 hover:bg-slate-50 transition-colors">
                    <div className="flex items-center gap-3.5">
                      <div
                        className={cn(
                          'w-8 h-8 rounded-lg flex items-center justify-center',
                          run.status === 'success'
                            ? 'bg-emerald-50 text-emerald-600'
                            : run.status === 'failed'
                              ? 'bg-red-50 text-red-600'
                              : 'bg-blue-50 text-blue-600'
                        )}
                      >
                        {run.status === 'success' ? (
                          <CheckCircle2 className="w-4 h-4" />
                        ) : run.status === 'failed' ? (
                          <XCircle className="w-4 h-4" />
                        ) : (
                          <Zap className="w-4 h-4" />
                        )}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-slate-900">
                          <span className="capitalize">{run.type}</span> Run
                        </p>
                        <p className="text-xs text-slate-500">
                          {formatDate(run.startedAt)}
                          {run.durationMs && ` · ${Math.round(run.durationMs / 1000)}s`}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <StatusBadge status={run.status} />
                      <span className="text-xs text-slate-400 font-mono">#{run.id.split('-').pop()}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center text-slate-500 text-sm">No runs recorded yet.</div>
            )}
          </div>
        </div>

        {/* Right column: Quick Actions + Recent Reports */}
        <div className="space-y-6">
          {/* Quick Actions */}
          <div className="space-y-3">
            <h3 className="text-base font-bold text-slate-900">Quick Actions</h3>
            <div className="grid grid-cols-1 gap-2">
              <button
                onClick={() => runMutation.mutate()}
                disabled={runMutation.isPending}
                className={cn(
                  'flex items-center gap-2.5 w-full p-3 text-white rounded-lg font-medium transition-all shadow-sm text-sm',
                  runMutation.isPending
                    ? 'bg-indigo-400 cursor-wait'
                    : 'bg-indigo-600 hover:bg-indigo-700'
                )}
              >
                {runMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Play className="w-4 h-4 fill-current" />
                )}
                {runMutation.isPending ? 'Triggering...' : 'Run Intelligence Cycle'}
              </button>
              <Link
                to={`/workspaces/${workspaceId}/feeds`}
                className="flex items-center gap-2.5 w-full p-3 bg-white border border-slate-200 text-slate-700 rounded-lg font-medium hover:bg-slate-50 transition-colors text-sm"
              >
                <Rss className="w-4 h-4" />
                View All Feeds
              </Link>
              <Link
                to={`/workspaces/${workspaceId}/content`}
                className="flex items-center gap-2.5 w-full p-3 bg-white border border-slate-200 text-slate-700 rounded-lg font-medium hover:bg-slate-50 transition-colors text-sm"
              >
                <FileText className="w-4 h-4" />
                View All Content
              </Link>
              <Link
                to={`/workspaces/${workspaceId}/reports`}
                className="flex items-center gap-2.5 w-full p-3 bg-white border border-slate-200 text-slate-700 rounded-lg font-medium hover:bg-slate-50 transition-colors text-sm"
              >
                <MessageSquare className="w-4 h-4" />
                View All Reports
              </Link>
            </div>
          </div>

          {/* Recent Reports */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-900">Recent Reports</h3>
              <Link
                to={`/workspaces/${workspaceId}/reports`}
                className="text-sm text-indigo-600 font-medium hover:underline flex items-center gap-1"
              >
                View all <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
              {reports && reports.length > 0 ? (
                <div className="divide-y divide-slate-100">
                  {reports.slice(0, 3).map((report) => (
                    <Link
                      key={report.id}
                      to={`/workspaces/${workspaceId}/reports/${report.id}`}
                      className="flex items-center justify-between p-3.5 hover:bg-slate-50 transition-colors"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-8 h-8 bg-indigo-50 rounded-lg flex items-center justify-center text-indigo-600 shrink-0">
                          <FileText className="w-4 h-4" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-slate-900 truncate">{report.title}</p>
                          <p className="text-xs text-slate-500">{formatDate(report.createdAt)}</p>
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-slate-400 shrink-0" />
                    </Link>
                  ))}
                </div>
              ) : (
                <div className="p-6 text-center text-slate-500 text-sm">No reports generated yet.</div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Run toast */}
      {runToast && (
        <div className="fixed bottom-6 right-6 z-[100]">
          <div
            className={cn(
              'flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg border text-sm font-medium',
              runToast.success
                ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                : 'bg-red-50 border-red-200 text-red-800'
            )}
          >
            {runToast.success ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            ) : (
              <XCircle className="w-4 h-4 text-red-600" />
            )}
            {runToast.message}
          </div>
        </div>
      )}
    </div>
  );
}

/* ---- Helper components ---- */

function OverviewStatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  color,
  bg,
}: {
  title: string;
  value: string | number;
  subtitle: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  bg: string;
}) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{title}</p>
        <div className={cn('p-1.5 rounded-lg', bg, color)}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <p className="text-xl font-bold text-slate-900 leading-tight">{value}</p>
      <p className="text-xs text-slate-500 mt-1">{subtitle}</p>
    </div>
  );
}

function formatStatus(status: string): string {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function formatRelativeDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffHours = Math.round(diffMs / (1000 * 60 * 60));

  if (diffHours < 0) return 'Overdue';
  if (diffHours < 1) return 'Less than 1h';
  if (diffHours < 24) return `In ${diffHours}h`;
  const diffDays = Math.round(diffHours / 24);
  return `In ${diffDays}d`;
}
