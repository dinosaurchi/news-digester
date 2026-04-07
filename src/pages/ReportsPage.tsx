import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useParams } from 'react-router-dom';
import { MessageSquare, Calendar, ChevronRight, FileText, Filter, Search } from 'lucide-react';
import { formatDate, cn } from '@/lib/utils';
import { Link } from 'react-router-dom';

export default function ReportsPage() {
  const params = useParams();
  const workspaceId = params.workspaceId as string;

  const { data: reports, isLoading } = useQuery({
    queryKey: ['reports', workspaceId],
    queryFn: () => api.reports.list(workspaceId)
  });

  if (isLoading) return <div className="space-y-6"><div className="h-10 w-48 bg-slate-200 animate-pulse rounded" /><div className="h-64 bg-white rounded-xl animate-pulse" /></div>;

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Intelligence Reports</h2>
          <p className="text-slate-500 mt-1">Access all generated report threads and conversational history.</p>
        </div>
      </div>

      <div className="flex items-center justify-between bg-white p-4 border border-slate-200 rounded-xl shadow-sm">
        <div className="relative w-96">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search reports..." 
            className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
          />
        </div>
        <button className="flex items-center gap-2 px-4 py-2 border border-slate-200 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors">
          <Filter className="w-4 h-4" />
          Filter by Date
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {reports?.map((report) => (
          <Link 
            key={report.id} 
            to={`/workspaces/${workspaceId}/reports/${report.id}`}
            className="group bg-white border border-slate-200 rounded-xl p-6 hover:border-indigo-500 hover:shadow-md transition-all flex items-center justify-between"
          >
            <div className="flex items-center gap-6">
              <div className="w-14 h-14 bg-indigo-50 rounded-xl flex items-center justify-center text-indigo-600 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                <MessageSquare className="w-7 h-7" />
              </div>
              <div className="space-y-1">
                <h3 className="text-lg font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">{report.title}</h3>
                <div className="flex items-center gap-4 text-sm text-slate-500">
                  <div className="flex items-center gap-1.5">
                    <Calendar className="w-4 h-4" />
                    {formatDate(report.createdAt)}
                  </div>
                  <div className="h-4 w-px bg-slate-200" />
                  <div className="flex items-center gap-1.5">
                    <FileText className="w-4 h-4" />
                    Period: {new Date(report.periodStart).toLocaleDateString()} - {new Date(report.periodEnd).toLocaleDateString()}
                  </div>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <span className={cn(
                "px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider",
                report.status === 'published' ? "bg-emerald-50 text-emerald-700 border border-emerald-100" : "bg-slate-100 text-slate-600 border border-slate-200"
              )}>
                {report.status}
              </span>
              <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-indigo-600 transition-colors" />
            </div>
          </Link>
        ))}
        {reports?.length === 0 && (
          <div className="p-12 text-center bg-white border border-slate-200 rounded-xl">
            <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-4">
              <MessageSquare className="w-8 h-8 text-slate-300" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">No reports yet</h3>
            <p className="text-slate-500">Reports will appear here once the intelligence cycle runs.</p>
          </div>
        )}
      </div>
    </div>
  );
}
