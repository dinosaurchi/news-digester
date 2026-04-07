'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useParams } from 'next/navigation';
import { 
  Activity, 
  Rss, 
  FileText, 
  MessageSquare, 
  Clock, 
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  Play,
  ChevronRight
} from 'lucide-react';
import Link from 'next/link';
import { formatDate, cn } from '@/lib/utils';
import { useAppStore } from '@/lib/store';
import { useEffect } from 'react';

export default function WorkspaceOverviewPage() {
  const params = useParams();
  const workspaceId = params.workspaceId as string;
  const { setCurrentWorkspace } = useAppStore();

  const { data: workspace, isLoading: wsLoading } = useQuery({
    queryKey: ['workspace', workspaceId],
    queryFn: () => api.workspaces.get(workspaceId)
  });

  const { data: runs } = useQuery({
    queryKey: ['runs', workspaceId],
    queryFn: () => api.runs.list(workspaceId)
  });

  const { data: reports } = useQuery({
    queryKey: ['reports', workspaceId],
    queryFn: () => api.reports.list(workspaceId)
  });

  useEffect(() => {
    if (workspace) setCurrentWorkspace(workspace);
  }, [workspace, setCurrentWorkspace]);

  if (wsLoading) return <div className="animate-pulse space-y-8"><div className="h-32 bg-white rounded-xl" /><div className="grid grid-cols-4 gap-6"><div className="h-24 bg-white rounded-xl" /></div></div>;

  return (
    <div className="space-y-8">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard 
          title="Workspace Health" 
          value="Healthy" 
          icon={CheckCircle2} 
          color="text-emerald-600" 
          bg="bg-emerald-50" 
        />
        <StatCard 
          title="Active Feeds" 
          value={workspace?.feedCount || 0} 
          icon={Rss} 
          color="text-indigo-600" 
          bg="bg-indigo-50" 
        />
        <StatCard 
          title="Reports Generated" 
          value={reports?.length || 0} 
          icon={MessageSquare} 
          color="text-amber-600" 
          bg="bg-amber-50" 
        />
        <StatCard 
          title="Next Run" 
          value={workspace?.nextRunAt ? formatDate(workspace.nextRunAt) : 'Manual'} 
          icon={Clock} 
          color="text-slate-600" 
          bg="bg-slate-50" 
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent Reports */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-slate-900">Recent Reports</h3>
            <Link href={`/workspaces/${workspaceId}/reports`} className="text-sm text-indigo-600 font-medium hover:underline flex items-center gap-1">
              View all <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            {reports && reports.length > 0 ? (
              <div className="divide-y divide-slate-100">
                {reports.slice(0, 3).map(report => (
                  <Link 
                    key={report.id} 
                    href={`/workspaces/${workspaceId}/reports/${report.id}`}
                    className="flex items-center justify-between p-4 hover:bg-slate-50 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 bg-indigo-50 rounded-lg flex items-center justify-center text-indigo-600">
                        <FileText className="w-5 h-5" />
                      </div>
                      <div>
                        <p className="font-medium text-slate-900">{report.title}</p>
                        <p className="text-xs text-slate-500">{formatDate(report.createdAt)}</p>
                      </div>
                    </div>
                    <ChevronRightIcon className="w-4 h-4 text-slate-400" />
                  </Link>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center text-slate-500">No reports generated yet.</div>
            )}
          </div>
        </div>

        {/* Quick Actions & Recent Runs */}
        <div className="space-y-8">
          <div className="space-y-4">
            <h3 className="text-lg font-bold text-slate-900">Quick Actions</h3>
            <div className="grid grid-cols-1 gap-3">
              <button className="flex items-center gap-3 w-full p-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition-colors shadow-sm">
                <Play className="w-4 h-4 fill-current" />
                Run Intelligence Cycle
              </button>
              <Link href={`/workspaces/${workspaceId}/feeds`} className="flex items-center gap-3 w-full p-3 bg-white border border-slate-200 text-slate-700 rounded-lg font-medium hover:bg-slate-50 transition-colors">
                <Rss className="w-4 h-4" />
                Manage Feeds
              </Link>
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="text-lg font-bold text-slate-900">Recent Runs</h3>
            <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
              {runs && runs.length > 0 ? (
                <div className="divide-y divide-slate-100">
                  {runs.slice(0, 3).map(run => (
                    <div key={run.id} className="p-4 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={cn(
                          "w-2 h-2 rounded-full",
                          run.status === 'success' ? 'bg-emerald-500' : 'bg-red-500'
                        )} />
                        <div>
                          <p className="text-sm font-medium text-slate-900 capitalize">{run.type} Run</p>
                          <p className="text-[10px] text-slate-500">{formatDate(run.startedAt)}</p>
                        </div>
                      </div>
                      <span className="text-xs font-mono text-slate-400">#{run.id.split('-')[1]}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-4 text-center text-slate-500 text-sm">No runs recorded.</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon: Icon, color, bg }: any) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm font-medium text-slate-500">{title}</p>
        <div className={cn("p-2 rounded-lg", bg, color)}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      <p className="text-2xl font-bold text-slate-900">{value}</p>
    </div>
  );
}

function ChevronRightIcon({ className }: { className?: string }) {
  return <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m9 18 6-6-6-6"/></svg>;
}
