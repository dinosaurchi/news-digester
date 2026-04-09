import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useParams } from 'react-router-dom';
import { Plus, Rss, Globe, Trash2, Edit2, Search, AlertCircle, Loader2 } from 'lucide-react';
import { formatDate, timeAgo, cn } from '@/lib/utils';
import { useState, useMemo } from 'react';
import { useForm, type Resolver } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { feedSchema, type FeedFormValues } from '@/lib/schemas/feeds';
import { PageHeader } from '@/components/ui/page-header';
import { StatusBadge } from '@/components/ui/status-badge';
import { EmptyState } from '@/components/ui/empty-state';
import { TableSkeleton, Skeleton } from '@/components/ui/loading-skeleton';
import { Sheet } from '@/components/ui/sheet';
import { ListEditor } from '@/components/ui/list-editor';
import { toast } from '@/components/ui/toast';
import type { FeedSource, FeedStatus } from '@/types';

type FeedStatusFilter = 'all' | FeedStatus;

const statusFilterOptions: { value: FeedStatusFilter; label: string }[] = [
  { value: 'all', label: 'All Status' },
  { value: 'healthy', label: 'Healthy' },
  { value: 'error', label: 'Error' },
  { value: 'disabled', label: 'Disabled' },
];

const typeIconMap: Record<string, React.ReactNode> = {
  rss: <Rss className="w-4 h-4" />,
  website: <Globe className="w-4 h-4" />,
  competitor: <AlertCircle className="w-4 h-4" />,
  blog: <Globe className="w-4 h-4" />,
};

const typeLabelMap: Record<string, string> = {
  rss: 'RSS',
  website: 'Website',
  competitor: 'Competitor',
  blog: 'Blog',
};

export default function FeedsPage() {
  const params = useParams();
  const workspaceId = params.workspaceId as string;
  const queryClient = useQueryClient();

  const [isSheetOpen, setIsSheetOpen] = useState(false);
  const [editingFeed, setEditingFeed] = useState<FeedSource | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<FeedStatusFilter>('all');
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  const { data: feeds, isLoading } = useQuery({
    queryKey: ['feeds', workspaceId],
    queryFn: () => api.feeds.list(workspaceId),
  });

  const addMutation = useMutation({
    mutationFn: (values: FeedFormValues) => api.feeds.add(workspaceId, values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['feeds', workspaceId] });
      closeSheet();
      toast.success('Feed source added successfully!');
    },
    onError: () => toast.error('Failed to add feed source.'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ feedId, values }: { feedId: string; values: Partial<FeedSource> }) => api.feeds.update(workspaceId, feedId, values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['feeds', workspaceId] });
      closeSheet();
      toast.success('Feed source updated successfully!');
    },
    onError: () => toast.error('Failed to update feed source.'),
  });

  const toggleMutation = useMutation({
    mutationFn: (feedId: string) => api.feeds.toggle(workspaceId, feedId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['feeds', workspaceId] });
    },
    onError: () => toast.error('Failed to toggle feed status.'),
  });

  const deleteMutation = useMutation({
    mutationFn: (feedId: string) => api.feeds.delete(workspaceId, feedId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['feeds', workspaceId] });
      setDeleteConfirmId(null);
      toast.success('Feed source deleted.');
    },
    onError: () => toast.error('Failed to delete feed source.'),
  });

  const { register, handleSubmit, reset, formState: { errors }, setValue, watch } = useForm<FeedFormValues>({
    resolver: zodResolver(feedSchema) as Resolver<FeedFormValues>,
    defaultValues: {
      type: 'rss',
      cadence: 'daily',
      tags: [],
    },
  });

  const openAddSheet = () => {
    setEditingFeed(null);
    reset({ name: '', url: '', type: 'rss', cadence: 'daily', tags: [] });
    setIsSheetOpen(true);
  };

  const openEditSheet = (feed: FeedSource) => {
    setEditingFeed(feed);
    reset({
      name: feed.name,
      url: feed.url,
      type: feed.type,
      cadence: feed.cadence,
      tags: feed.tags || [],
    });
    setIsSheetOpen(true);
  };

  const closeSheet = () => {
    setIsSheetOpen(false);
    setEditingFeed(null);
  };

  const onSubmit = (values: FeedFormValues) => {
    if (editingFeed) {
      updateMutation.mutate({ feedId: editingFeed.id, values });
    } else {
      addMutation.mutate(values);
    }
  };

  const isSubmitting = addMutation.isPending || updateMutation.isPending;

  const filteredFeeds = useMemo(() => {
    if (!feeds) return [];
    let result = [...feeds];
    if (statusFilter !== 'all') {
      result = result.filter((f) => f.status === statusFilter);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (f) => f.name.toLowerCase().includes(q) || f.url.toLowerCase().includes(q)
      );
    }
    return result;
  }, [feeds, statusFilter, searchQuery]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-72" />
        <TableSkeleton rows={6} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Input Feeds"
        description="Manage the sources that feed into your intelligence reports."
        actions={
          <button
            onClick={openAddSheet}
            className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" />
            Add Feed Source
          </button>
        }
      />

      {/* Filters */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by name or URL..."
            className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all"
          />
        </div>
        <div className="flex items-center gap-1.5">
          {statusFilterOptions.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setStatusFilter(opt.value)}
              className={cn(
                'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
                statusFilter === opt.value
                  ? 'bg-indigo-100 text-indigo-700'
                  : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Feed Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        {filteredFeeds.length === 0 ? (
          <EmptyState
            icon={Rss}
            title={feeds?.length === 0 ? 'No feeds added' : 'No matching feeds'}
            description={
              feeds?.length === 0
                ? 'Start by adding your first news source or RSS feed.'
                : 'Try adjusting your search or filter.'
            }
            action={
              feeds?.length === 0 ? (
                <button
                  onClick={openAddSheet}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg font-medium text-sm"
                >
                  Add First Feed
                </button>
              ) : undefined
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="px-6 py-3.5 text-xs font-bold text-slate-500 uppercase tracking-wider">Name</th>
                  <th className="px-6 py-3.5 text-xs font-bold text-slate-500 uppercase tracking-wider">Type</th>
                  <th className="px-6 py-3.5 text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3.5 text-xs font-bold text-slate-500 uppercase tracking-wider">Cadence</th>
                  <th className="px-6 py-3.5 text-xs font-bold text-slate-500 uppercase tracking-wider">Last Fetched</th>
                  <th className="px-6 py-3.5 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredFeeds.map((feed) => (
                  <tr key={feed.id} className="hover:bg-slate-50/80 transition-colors group">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-slate-100 rounded-lg flex items-center justify-center text-slate-500 shrink-0">
                          {typeIconMap[feed.type]}
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-slate-900 truncate">{feed.name}</p>
                          <p className="text-xs text-slate-400 truncate max-w-[200px]" title={feed.url}>{feed.url}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-xs font-medium text-slate-600 bg-slate-100 px-2 py-1 rounded capitalize">
                        {typeLabelMap[feed.type] || feed.type}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="relative group/status">
                        <StatusBadge status={feed.status} />
                        {feed.status === 'error' && feed.lastError && (
                          <div className="absolute left-0 top-full mt-1 z-20 hidden group-hover/status:block">
                            <div className="bg-slate-800 text-white text-xs rounded-lg p-2 max-w-[250px] shadow-lg">
                              {feed.lastError}
                            </div>
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-500 capitalize">{feed.cadence}</td>
                    <td className="px-6 py-4">
                      {feed.status === 'error' ? (
                        <div className="space-y-1">
                          {feed.lastErrorAt && (
                            <span className="text-xs font-medium text-red-600">
                              Errored {timeAgo(feed.lastErrorAt)}
                            </span>
                          )}
                          {feed.lastError && (
                            <p className="text-xs text-red-500/80 truncate max-w-[180px]" title={feed.lastError}>
                              {feed.lastError}
                            </p>
                          )}
                        </div>
                      ) : (
                        <span className="text-sm text-slate-500">
                          {feed.lastFetchedAt ? formatDate(feed.lastFetchedAt) : 'Never'}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        {/* Enable/Disable Toggle */}
                        <button
                          onClick={() => toggleMutation.mutate(feed.id)}
                          className={cn(
                            'px-2 py-1 text-xs font-medium rounded-md transition-colors',
                            feed.status === 'disabled'
                              ? 'text-emerald-600 hover:bg-emerald-50'
                              : 'text-slate-500 hover:bg-slate-100'
                          )}
                          title={feed.status === 'disabled' ? 'Enable feed' : 'Disable feed'}
                        >
                          {feed.status === 'disabled' ? 'Enable' : 'Disable'}
                        </button>
                        <button
                          onClick={() => openEditSheet(feed)}
                          className="p-1.5 hover:bg-slate-100 text-slate-500 rounded-lg transition-colors"
                          title="Edit feed"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setDeleteConfirmId(feed.id)}
                          className="p-1.5 hover:bg-red-50 text-red-500 rounded-lg transition-colors"
                          title="Delete feed"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add/Edit Feed Sheet */}
      <Sheet
        open={isSheetOpen}
        onOpenChange={closeSheet}
        title={editingFeed ? 'Edit Feed Source' : 'Add Feed Source'}
        description={editingFeed ? 'Update the feed source configuration.' : 'Add a new news source or RSS feed to monitor.'}
      >
        <form onSubmit={handleSubmit(onSubmit as (data: FeedFormValues) => void)} className="space-y-5">
          <div className="space-y-1.5">
            <label className="text-sm font-semibold text-slate-700">Feed Name <span className="text-red-400">*</span></label>
            <input
              {...register('name')}
              placeholder="e.g. TechCrunch Enterprise"
              className={cn(
                'w-full px-4 py-2.5 border rounded-lg outline-none transition-all text-sm',
                errors.name ? 'border-red-300 focus:ring-2 focus:ring-red-500/10' : 'border-slate-200 focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500'
              )}
            />
            {errors.name && <p className="text-xs text-red-500 font-medium">{errors.name.message}</p>}
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-semibold text-slate-700">Feed URL <span className="text-red-400">*</span></label>
            <input
              {...register('url')}
              placeholder="https://example.com/feed"
              className={cn(
                'w-full px-4 py-2.5 border rounded-lg outline-none transition-all text-sm',
                errors.url ? 'border-red-300 focus:ring-2 focus:ring-red-500/10' : 'border-slate-200 focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500'
              )}
            />
            {errors.url && <p className="text-xs text-red-500 font-medium">{errors.url.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-slate-700">Source Type <span className="text-red-400">*</span></label>
              <select
                {...register('type')}
                className="w-full px-4 py-2.5 border border-slate-200 rounded-lg outline-none text-sm bg-white focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all"
              >
                <option value="rss">RSS Feed</option>
                <option value="website">Website</option>
                <option value="competitor">Competitor Page</option>
                <option value="blog">Blog Source</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-slate-700">Fetch Cadence <span className="text-red-400">*</span></label>
              <select
                {...register('cadence')}
                className="w-full px-4 py-2.5 border border-slate-200 rounded-lg outline-none text-sm bg-white focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all"
              >
                <option value="hourly">Hourly</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
              </select>
            </div>
          </div>

          <ListEditor
            label="Tags"
            description="Optional tags to categorize this feed."
            items={watch('tags') || []}
            onChange={(items) => setValue('tags', items, { shouldDirty: true })}
            placeholder="e.g. tech, enterprise"
          />

          <div className="pt-4 border-t border-slate-200 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={closeSheet}
              className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white rounded-lg text-sm font-bold transition-all shadow-sm"
            >
              {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
              {editingFeed ? 'Update Source' : 'Add Source'}
            </button>
          </div>
        </form>
      </Sheet>

      {/* Delete Confirmation Dialog */}
      {deleteConfirmId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" onClick={() => setDeleteConfirmId(null)} />
          <div className="relative w-full max-w-md bg-white rounded-2xl shadow-2xl p-6 space-y-4">
            <div className="flex items-center gap-3 text-red-600">
              <AlertCircle className="w-6 h-6" />
              <h3 className="text-lg font-bold text-slate-900">Delete Feed Source</h3>
            </div>
            <p className="text-sm text-slate-600">
              Are you sure you want to delete this feed source? This action cannot be undone and all historical data from this source will be removed.
            </p>
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setDeleteConfirmId(null)}
                className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteMutation.mutate(deleteConfirmId)}
                disabled={deleteMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-red-300 text-white rounded-lg text-sm font-bold transition-colors"
              >
                {deleteMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
