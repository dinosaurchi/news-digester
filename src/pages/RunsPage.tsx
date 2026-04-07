import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useParams } from 'react-router-dom';
import { Play, CheckCircle2, XCircle, Loader2, Info } from 'lucide-react';
import { formatDate, cn } from '@/lib/utils';

export default function RunsPage() {
  const params = useParams();
  const workspaceId = params.workspaceId as string;
  const queryClient = useQueryClient();

  const { data: runs, isLoading } = useQuery({
    queryKey: ['runs', workspaceId],
    queryFn: () => api.runs.list(workspaceId)
  });

  const triggerMutation = useMutation({
    mutationFn: () => api.runs.trigger(workspaceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['runs', workspaceId] });
    }
  });

  if (isLoading) return <div className="space-y-6"><div className="h-10 w-48 bg-slate-200 animate-pulse rounded" /><div className="h-64 bg-white rounded-xl animate-pulse" /></div>;

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Operational Runs</h2>
          <p className="text-slate-500 mt-1">Monitor intelligence cycle execution and system logs.</p>
        </div>
        <button 
          onClick={() => triggerMutation.mutate()}
          disabled={triggerMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white rounded-lg font-medium transition-colors shadow-sm"
        >
          {triggerMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
          Trigger Manual Run
        </button>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Run ID</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Type</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Started At</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Duration</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Impact</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {runs?.map((run) => (
              <tr key={run.id} className="hover:bg-slate-50 transition-colors group">
                <td className="px-6 py-4">
                  <span className="text-sm font-mono text-slate-600">#{run.id}</span>
                </td>
                <td className="px-6 py-4">
                  <span className="text-xs font-medium text-slate-600 bg-slate-100 px-2 py-1 rounded capitalize">
                    {run.type}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-1.5">
                    {run.status === 'success' ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    ) : run.status === 'failed' ? (
                      <XCircle className="w-4 h-4 text-red-500" />
                    ) : (
                      <Loader2 className="w-4 h-4 text-indigo-500 animate-spin" />
                    )}
                    <span className={cn(
                      "text-xs font-medium capitalize",
                      run.status === 'success' ? 'text-emerald-700' : run.status === 'failed' ? 'text-red-700' : 'text-indigo-700'
                    )}>
                      {run.status}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-slate-500">
                  {formatDate(run.startedAt)}
                </td>
                <td className="px-6 py-4 text-sm text-slate-500">
                  {run.durationMs ? `${Math.round(run.durationMs / 1000)}s` : '-'}
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3 text-[10px] font-bold text-slate-400 uppercase">
                    <span>{run.affectedCounts.feeds} Feeds</span>
                    <span>{run.affectedCounts.articles} Items</span>
                    <span>{run.affectedCounts.reports} Rep</span>
                  </div>
                </td>
                <td className="px-6 py-4 text-right">
                  <button className="p-1.5 hover:bg-slate-200 text-slate-600 rounded transition-colors">
                    <Info className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
