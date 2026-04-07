'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Plus, Search, MoreVertical, ExternalLink, Clock, Rss, MessageSquare } from 'lucide-react';
import Link from 'next/link';
import { formatDate } from '@/lib/utils';

export default function WorkspacesPage() {
  const { data: workspaces, isLoading } = useQuery({
    queryKey: ['workspaces'],
    queryFn: api.workspaces.list
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-10 w-48 bg-slate-200 animate-pulse rounded" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-48 bg-white border border-slate-200 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Workspaces</h2>
          <p className="text-slate-500 mt-1">Manage your customer reporting environments.</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors shadow-sm">
          <Plus className="w-4 h-4" />
          Create Workspace
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {workspaces?.map((ws) => (
          <Link 
            key={ws.id} 
            href={`/workspaces/${ws.id}`}
            className="group bg-white border border-slate-200 rounded-xl p-6 hover:border-indigo-500 hover:shadow-md transition-all"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="w-12 h-12 bg-indigo-50 rounded-lg flex items-center justify-center text-indigo-600 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                <BriefcaseIcon className="w-6 h-6" />
              </div>
              <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                ws.status === 'active' ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' : 
                'bg-slate-100 text-slate-600 border border-slate-200'
              }`}>
                {ws.status.charAt(0).toUpperCase() + ws.status.slice(1)}
              </span>
            </div>

            <h3 className="text-lg font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">{ws.name}</h3>
            <p className="text-sm text-slate-500 mb-6">{ws.customer}</p>

            <div className="grid grid-cols-2 gap-4 pt-4 border-t border-slate-100">
              <div className="flex items-center gap-2 text-slate-500">
                <Rss className="w-4 h-4" />
                <span className="text-xs font-medium">{ws.feedCount} Feeds</span>
              </div>
              <div className="flex items-center gap-2 text-slate-500">
                <MessageSquare className="w-4 h-4" />
                <span className="text-xs font-medium">Reports</span>
              </div>
            </div>

            <div className="mt-4 flex items-center gap-2 text-[10px] text-slate-400 uppercase tracking-wider font-bold">
              <Clock className="w-3 h-3" />
              Last report: {ws.lastReportAt ? formatDate(ws.lastReportAt) : 'Never'}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

function BriefcaseIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="20" height="14" x="2" y="7" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
  );
}
