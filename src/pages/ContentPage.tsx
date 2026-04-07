import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useParams } from 'react-router-dom';
import { Search, Filter, ExternalLink, Info, CheckCircle2, XCircle, Clock } from 'lucide-react';
import { formatDate, cn } from '@/lib/utils';
import { useState } from 'react';

export default function ContentPage() {
  const params = useParams();
  const workspaceId = params.workspaceId as string;
  const [search, setSearch] = useState('');

  const { data: content, isLoading } = useQuery({
    queryKey: ['content', workspaceId],
    queryFn: () => api.content.list(workspaceId)
  });

  const filteredContent = content?.filter(item => 
    item.title.toLowerCase().includes(search.toLowerCase()) || 
    item.source.toLowerCase().includes(search.toLowerCase())
  );

  if (isLoading) return <div className="space-y-6"><div className="h-10 w-48 bg-slate-200 animate-pulse rounded" /><div className="h-96 bg-white rounded-xl animate-pulse" /></div>;

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Content Inspection</h2>
          <p className="text-slate-500 mt-1">Review and debug fetched content items and their relevance scores.</p>
        </div>
      </div>

      <div className="flex flex-col md:flex-row gap-4 items-center justify-between bg-white p-4 border border-slate-200 rounded-xl shadow-sm">
        <div className="relative w-full md:w-96">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search content..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
          />
        </div>
        <div className="flex items-center gap-2 w-full md:w-auto">
          <button className="flex items-center gap-2 px-4 py-2 border border-slate-200 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors">
            <Filter className="w-4 h-4" />
            Filters
          </button>
          <div className="h-8 w-px bg-slate-200 mx-2" />
          <span className="text-sm text-slate-500 whitespace-nowrap">
            Showing <strong>{filteredContent?.length || 0}</strong> items
          </span>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Content Item</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Source</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Scores</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Published</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filteredContent?.map((item) => (
              <tr key={item.id} className="hover:bg-slate-50 transition-colors group">
                <td className="px-6 py-4 max-w-md">
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-slate-900 line-clamp-1">{item.title}</p>
                    <p className="text-xs text-slate-500 line-clamp-2">{item.snippet}</p>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className="text-xs font-medium text-slate-600 bg-slate-100 px-2 py-1 rounded">
                    {item.source}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="text-center">
                      <p className="text-[10px] font-bold text-slate-400 uppercase">Final</p>
                      <p className={cn(
                        "text-sm font-bold",
                        item.finalScore > 0.8 ? "text-emerald-600" : item.finalScore > 0.5 ? "text-amber-600" : "text-red-600"
                      )}>{Math.round(item.finalScore * 100)}%</p>
                    </div>
                    <div className="h-6 w-px bg-slate-200" />
                    <div className="text-center">
                      <p className="text-[10px] font-bold text-slate-400 uppercase">LLM</p>
                      <p className="text-xs font-medium text-slate-600">{Math.round(item.llmScore * 100)}%</p>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-1.5">
                    {item.status === 'included' ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    ) : item.status === 'excluded' ? (
                      <XCircle className="w-4 h-4 text-slate-400" />
                    ) : (
                      <Clock className="w-4 h-4 text-amber-500" />
                    )}
                    <span className={cn(
                      "text-xs font-medium capitalize",
                      item.status === 'included' ? 'text-emerald-700' : 'text-slate-600'
                    )}>
                      {item.status}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4 text-xs text-slate-500">
                  {formatDate(item.publishedAt)}
                </td>
                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <a 
                      href={item.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="p-1.5 hover:bg-slate-200 text-slate-600 rounded transition-colors"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                    <button className="p-1.5 hover:bg-slate-200 text-slate-600 rounded transition-colors">
                      <Info className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
