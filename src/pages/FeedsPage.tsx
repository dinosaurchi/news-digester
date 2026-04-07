import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useParams } from 'react-router-dom';
import { Plus, Rss, Globe, Trash2, Edit2, AlertCircle, CheckCircle2, X, Loader2 } from 'lucide-react';
import { formatDate, cn } from '@/lib/utils';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { motion, AnimatePresence } from 'motion/react';

const feedSchema = z.object({
  name: z.string().min(1, 'Feed name is required'),
  url: z.string().url('Please enter a valid URL (e.g., https://example.com/feed)'),
  type: z.enum(['rss', 'website', 'competitor', 'blog']),
  cadence: z.enum(['hourly', 'daily', 'weekly']),
});

type FeedFormValues = z.infer<typeof feedSchema>;

export default function FeedsPage() {
  const params = useParams();
  const workspaceId = params.workspaceId as string;
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);

  const { data: feeds, isLoading } = useQuery({
    queryKey: ['feeds', workspaceId],
    queryFn: () => api.feeds.list(workspaceId)
  });

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FeedFormValues>({
    resolver: zodResolver(feedSchema),
    defaultValues: {
      type: 'rss',
      cadence: 'daily',
    }
  });

  const addMutation = useMutation({
    mutationFn: (values: FeedFormValues) => api.feeds.add(workspaceId, values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['feeds', workspaceId] });
      setIsModalOpen(false);
      reset();
    }
  });

  const onSubmit = (values: FeedFormValues) => {
    addMutation.mutate(values);
  };

  if (isLoading) return <div className="space-y-6"><div className="h-10 w-48 bg-slate-200 animate-pulse rounded" /><div className="h-64 bg-white rounded-xl animate-pulse" /></div>;

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Input Feeds</h2>
          <p className="text-slate-500 mt-1">Manage the sources that feed into your intelligence reports.</p>
        </div>
        <button 
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors shadow-sm"
        >
          <Plus className="w-4 h-4" />
          Add Feed Source
        </button>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Source Name</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Type</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Last Fetched</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Cadence</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {feeds?.map((feed) => (
              <tr key={feed.id} className="hover:bg-slate-50 transition-colors group">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-slate-100 rounded flex items-center justify-center text-slate-500">
                      {feed.type === 'rss' ? <Rss className="w-4 h-4" /> : <Globe className="w-4 h-4" />}
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{feed.name}</p>
                      <p className="text-xs text-slate-400 truncate max-w-[200px]">{feed.url}</p>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className="text-xs font-medium text-slate-600 bg-slate-100 px-2 py-1 rounded capitalize">
                    {feed.type}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-1.5">
                    {feed.status === 'healthy' ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-red-500" />
                    )}
                    <span className={cn(
                      "text-xs font-medium",
                      feed.status === 'healthy' ? 'text-emerald-700' : 'text-red-700'
                    )}>
                      {feed.status.charAt(0).toUpperCase() + feed.status.slice(1)}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-slate-500">
                  {feed.lastFetchedAt ? formatDate(feed.lastFetchedAt) : 'Never'}
                </td>
                <td className="px-6 py-4 text-sm text-slate-500 capitalize">
                  {feed.cadence}
                </td>
                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button className="p-1.5 hover:bg-slate-200 text-slate-600 rounded transition-colors">
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button className="p-1.5 hover:bg-red-100 text-red-600 rounded transition-colors">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {feeds?.length === 0 && (
          <div className="p-12 text-center">
            <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-4">
              <Rss className="w-8 h-8 text-slate-300" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">No feeds added</h3>
            <p className="text-slate-500 mb-6">Start by adding your first news source or RSS feed.</p>
            <button 
              onClick={() => setIsModalOpen(true)}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg font-medium"
            >
              Add First Feed
            </button>
          </div>
        )}
      </div>

      {/* Add Feed Modal */}
      <AnimatePresence>
        {isModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsModalOpen(false)}
              className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"
            />
            <motion.div 
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="relative w-full max-w-lg bg-white rounded-2xl shadow-2xl overflow-hidden"
            >
              <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                <h3 className="text-lg font-bold text-slate-900">Add Feed Source</h3>
                <button 
                  onClick={() => setIsModalOpen(false)}
                  className="p-1 hover:bg-slate-200 rounded-full transition-colors"
                >
                  <X className="w-5 h-5 text-slate-500" />
                </button>
              </div>

              <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-4">
                <div className="space-y-1.5">
                  <label className="text-sm font-semibold text-slate-700">Feed Name</label>
                  <input 
                    {...register('name')}
                    placeholder="e.g. TechCrunch Enterprise"
                    className={cn(
                      "w-full px-4 py-2 border rounded-lg outline-none transition-all text-sm",
                      errors.name ? "border-red-500 focus:ring-2 focus:ring-red-500/10" : "border-slate-200 focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500"
                    )}
                  />
                  {errors.name && <p className="text-xs text-red-500 font-medium">{errors.name.message}</p>}
                </div>

                <div className="space-y-1.5">
                  <label className="text-sm font-semibold text-slate-700">Feed URL</label>
                  <input 
                    {...register('url')}
                    placeholder="https://example.com/feed"
                    className={cn(
                      "w-full px-4 py-2 border rounded-lg outline-none transition-all text-sm",
                      errors.url ? "border-red-500 focus:ring-2 focus:ring-red-500/10" : "border-slate-200 focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500"
                    )}
                  />
                  {errors.url && <p className="text-xs text-red-500 font-medium">{errors.url.message}</p>}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-sm font-semibold text-slate-700">Source Type</label>
                    <select 
                      {...register('type')}
                      className="w-full px-4 py-2 border border-slate-200 rounded-lg outline-none text-sm bg-white"
                    >
                      <option value="rss">RSS Feed</option>
                      <option value="website">Website</option>
                      <option value="competitor">Competitor Page</option>
                      <option value="blog">Blog Source</option>
                    </select>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-sm font-semibold text-slate-700">Fetch Cadence</label>
                    <select 
                      {...register('cadence')}
                      className="w-full px-4 py-2 border border-slate-200 rounded-lg outline-none text-sm bg-white"
                    >
                      <option value="hourly">Hourly</option>
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                    </select>
                  </div>
                </div>

                <div className="pt-4 flex items-center justify-end gap-3">
                  <button 
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  <button 
                    type="submit"
                    disabled={addMutation.isPending}
                    className="flex items-center gap-2 px-6 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white rounded-lg text-sm font-bold transition-all shadow-sm"
                  >
                    {addMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                    Add Source
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
