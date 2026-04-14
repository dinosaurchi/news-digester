import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Search, ExternalLink, ChevronUp, ChevronDown, Info, FileText, FilterX,
  ArrowUpDown, Trash2, AlertCircle, Loader2,
} from 'lucide-react';
import { formatDateOnly, cn } from '@/lib/utils';
import { useState, useMemo } from 'react';
import { toast } from '@/components/ui/toast';
import { PageHeader } from '@/components/ui/page-header';
import { StatusBadge } from '@/components/ui/status-badge';
import { EmptyState } from '@/components/ui/empty-state';
import { Skeleton } from '@/components/ui/loading-skeleton';
import { ScoreBar } from '@/components/ui/score-bar';
import type { ContentStatus, ContentType } from '@/lib/types';
import type { ContentFilters } from '@/types';

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

type DatePreset = 'all' | 'today' | '7d' | '30d';

const PAGE_SIZE = 10;

type SortKey =
  | 'title'
  | 'source'
  | 'publishedAt'
  | 'type'
  | 'relevanceScore'
  | 'bm25Score'
  | 'finalScore'
  | 'status';
type SortDir = 'asc' | 'desc';

const contentTypeLabels: Record<ContentType, string> = {
  news: 'News',
  article: 'Article',
  press_release: 'Press Release',
  blog: 'Blog',
  competitor: 'Competitor',
  social: 'Social',
};

const contentTypeStyles: Record<ContentType, string> = {
  news: 'bg-blue-50 text-blue-700 border-blue-200',
  article: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  press_release: 'bg-purple-50 text-purple-700 border-purple-200',
  blog: 'bg-cyan-50 text-cyan-700 border-cyan-200',
  competitor: 'bg-orange-50 text-orange-700 border-orange-200',
  social: 'bg-pink-50 text-pink-700 border-pink-200',
};

const datePresets: { value: DatePreset; label: string }[] = [
  { value: 'all', label: 'All time' },
  { value: 'today', label: 'Today' },
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function getDateRange(preset: DatePreset): Partial<Pick<ContentFilters, 'dateFrom' | 'dateTo'>> {
  const now = new Date();
  switch (preset) {
    case 'today': {
      const s = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      return { dateFrom: s.toISOString(), dateTo: now.toISOString() };
    }
    case '7d':
      return { dateFrom: new Date(now.getTime() - 7 * 86400000).toISOString() };
    case '30d':
      return { dateFrom: new Date(now.getTime() - 30 * 86400000).toISOString() };
    default:
      return {};
  }
}

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

function SortableTh({
  label,
  column,
  sortKey,
  sortDir,
  onSort,
  className,
}: {
  label: string;
  column: SortKey;
  sortKey: SortKey;
  sortDir: SortDir;
  onSort: (k: SortKey) => void;
  className?: string;
}) {
  const active = sortKey === column;
  return (
    <th
      className={cn(
        'px-3 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider select-none cursor-pointer hover:text-slate-700 transition-colors',
        className,
      )}
      onClick={() => onSort(column)}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        {active ? (
          sortDir === 'asc' ? (
            <ChevronUp className="w-3 h-3 text-indigo-500" />
          ) : (
            <ChevronDown className="w-3 h-3 text-indigo-500" />
          )
        ) : (
          <ArrowUpDown className="w-3 h-3 text-slate-300" />
        )}
      </span>
    </th>
  );
}

function ContentTypeBadge({ type }: { type: ContentType }) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide rounded border',
        contentTypeStyles[type],
      )}
    >
      {contentTypeLabels[type]}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  Content Table Skeleton                                              */
/* ------------------------------------------------------------------ */

function ContentTableSkeleton() {
  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse min-w-[900px]">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              {Array.from({ length: 10 }).map((_, i) => (
                <th key={i} className="px-3 py-2.5">
                  <Skeleton className="h-3 w-16" />
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {Array.from({ length: 8 }).map((_, i) => (
              <tr key={i} className="hover:bg-slate-50">
                {Array.from({ length: 10 }).map((_, j) => (
                  <td key={j} className="px-3 py-2.5">
                    <Skeleton className="h-4 w-full" />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ================================================================== */
/*  ContentPage                                                        */
/* ================================================================== */

export default function ContentPage() {
  const params = useParams();
  const workspaceId = params.workspaceId as string;
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  /* ---- filter state ---- */
  const [source, setSource] = useState('');
  const [statusFilter, setStatusFilter] = useState<ContentStatus | 'all'>('all');
  const [typeFilter, setTypeFilter] = useState<ContentType | 'all'>('all');
  const [minScore, setMinScore] = useState('');
  const [datePreset, setDatePreset] = useState<DatePreset>('all');

  /* ---- sort state ---- */
  const [sortKey, setSortKey] = useState<SortKey>('publishedAt');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  /* ---- pagination ---- */
  const [page, setPage] = useState(1);

  /* ---- delete confirmation ---- */
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  /* ---- computed filters ---- */
  const filters: ContentFilters = useMemo(() => {
    const dr = getDateRange(datePreset);
    return {
      ...(statusFilter !== 'all' ? { status: statusFilter } : {}),
      ...(typeFilter !== 'all' ? { type: typeFilter } : {}),
      ...(source ? { source } : {}),
      ...(minScore ? { minScore: Number(minScore) / 100 } : {}),
      ...dr,
    };
  }, [statusFilter, typeFilter, source, minScore, datePreset]);

  const hasActiveFilters =
    source || statusFilter !== 'all' || typeFilter !== 'all' || minScore || datePreset !== 'all';

  const clearFilters = () => {
    setSource('');
    setStatusFilter('all');
    setTypeFilter('all');
    setMinScore('');
    setDatePreset('all');
    setPage(1);
  };

  /* ---- data ---- */
  const { data: content, isLoading } = useQuery({
    queryKey: ['content', workspaceId, filters],
    queryFn: () => api.content.list(workspaceId, filters),
  });

  /* ---- delete mutation ---- */
  const deleteMutation = useMutation({
    mutationFn: (itemId: string) => api.content.delete(itemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['content'] });
      setDeleteConfirmId(null);
      toast.success('Content item deleted.');
    },
    onError: () => toast.error('Failed to delete content item.'),
  });

  /* ---- sort ---- */
  const sorted = useMemo(() => {
    if (!content) return [];
    return [...content].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (typeof av === 'string' && typeof bv === 'string') {
        return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      if (typeof av === 'number' && typeof bv === 'number') {
        return sortDir === 'asc' ? av - bv : bv - av;
      }
      return 0;
    });
  }, [content, sortKey, sortDir]);

  /* ---- pagination ---- */
  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const paged = sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => (d === 'asc' ? 'desc' : 'asc'));
    else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  /* ---- loading ---- */
  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Content Inspection" description="Review and debug fetched content items and their relevance scores." />
        <Skeleton className="h-14 w-full rounded-xl" />
        <ContentTableSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ---- Header ---- */}
      <PageHeader title="Content Inspection" description="Review and debug fetched content items and their relevance scores." />

      {/* ---- Filter Bar ---- */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-4 space-y-3">
        {/* Row 1: search + presets + clear */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px] max-w-xs">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search source..."
              value={source}
              onChange={e => { setSource(e.target.value); setPage(1); }}
              className="w-full pl-9 pr-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300"
            />
          </div>

          {/* date presets */}
          <div className="flex items-center gap-1 bg-slate-50 rounded-lg p-0.5 border border-slate-200">
            {datePresets.map(p => (
              <button
                key={p.value}
                onClick={() => { setDatePreset(p.value); setPage(1); }}
                className={cn(
                  'px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
                  datePreset === p.value
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-500 hover:text-slate-700',
                )}
              >
                {p.label}
              </button>
            ))}
          </div>

          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-500 hover:text-red-600 border border-slate-200 hover:border-red-200 rounded-lg transition-colors"
            >
              <FilterX className="w-3.5 h-3.5" />
              Clear filters
            </button>
          )}

          <span className="ml-auto text-xs text-slate-400 tabular-nums">
            {sorted.length} item{sorted.length !== 1 ? 's' : ''}
          </span>
        </div>

        {/* Row 2: dropdowns + min score */}
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={statusFilter}
            onChange={e => { setStatusFilter(e.target.value as ContentStatus | 'all'); setPage(1); }}
            className="text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
          >
            <option value="all">All Statuses</option>
            <option value="included">Included</option>
            <option value="excluded">Excluded</option>
            <option value="pending">Pending</option>
          </select>

          <select
            value={typeFilter}
            onChange={e => { setTypeFilter(e.target.value as ContentType | 'all'); setPage(1); }}
            className="text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
          >
            <option value="all">All Types</option>
            <option value="news">News</option>
            <option value="article">Article</option>
            <option value="press_release">Press Release</option>
            <option value="blog">Blog</option>
            <option value="competitor">Competitor</option>
            <option value="social">Social</option>
          </select>

          <div className="relative">
            <input
              type="number"
              min={0}
              max={100}
              placeholder="Min score"
              value={minScore}
              onChange={e => { setMinScore(e.target.value); setPage(1); }}
              className="w-28 text-sm bg-slate-50 border border-slate-200 rounded-lg pl-3 pr-7 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 tabular-nums"
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-bold text-slate-400">/100</span>
          </div>
        </div>
      </div>

      {/* ---- Table or Empty ---- */}
      {sorted.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No content found"
          description={
            hasActiveFilters
              ? 'Try adjusting your filters to see more results.'
              : 'No content items have been fetched yet.'
          }
          action={
            hasActiveFilters ? (
              <button onClick={clearFilters} className="px-4 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors">
                Clear filters
              </button>
            ) : undefined
          }
        />
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[1020px]">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <SortableTh label="Title" column="title" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} className="min-w-[200px]" />
                  <SortableTh label="Published" column="publishedAt" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                  <SortableTh label="Type" column="type" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                  <SortableTh label="Relevance" column="relevanceScore" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} className="min-w-[90px]" />
                  <SortableTh label="BM25" column="bm25Score" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} className="min-w-[70px]" />
                  <SortableTh label="Final" column="finalScore" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} className="min-w-[80px]" />
                  <SortableTh label="Status" column="status" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                  <th className="px-3 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Cluster</th>
                  <th className="px-3 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {paged.map(item => (
                  <tr
                    key={item.id}
                    className="hover:bg-slate-50/70 transition-colors cursor-pointer group"
                    onClick={() => navigate(`/workspaces/${workspaceId}/content/${item.id}`)}
                  >
                    {/* Title */}
                    <td className="px-3 py-2.5 max-w-[220px]">
                      <p className="text-sm font-medium text-slate-900 line-clamp-1 group-hover:text-indigo-600 transition-colors">
                        {item.title}
                      </p>
                    </td>
                    {/* Published */}
                    <td className="px-3 py-2.5">
                      <span className="text-xs text-slate-500 tabular-nums">{formatDateOnly(item.publishedAt)}</span>
                    </td>
                    {/* Type */}
                    <td className="px-3 py-2.5">
                      <ContentTypeBadge type={item.type} />
                    </td>
                    {/* Relevance Score */}
                    <td className="px-3 py-2.5">
                      <ScoreBar score={item.relevanceScore * 100} size="sm" />
                    </td>
                    {/* LLM Score */}
                    <td className="px-3 py-2.5">
                      <ScoreBar score={item.bm25Score * 100} size="sm" showBar={false} />
                    </td>
                    {/* Final Score */}
                    <td className="px-3 py-2.5">
                      <ScoreBar score={item.finalScore * 100} size="sm" bold />
                    </td>
                    {/* Status */}
                    <td className="px-3 py-2.5">
                      <StatusBadge status={item.status} />
                    </td>
                    {/* Cluster */}
                    <td className="px-3 py-2.5">
                      {item.clusterId ? (
                        <span className="text-[10px] font-mono text-slate-400 bg-slate-50 px-1.5 py-0.5 rounded">
                          {item.clusterId}
                        </span>
                      ) : (
                        <span className="text-slate-300">—</span>
                      )}
                    </td>
                    {/* Actions */}
                    <td className="px-3 py-2.5 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <a
                          href={item.sourceUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={e => e.stopPropagation()}
                          className="p-1 hover:bg-slate-200 text-slate-400 hover:text-slate-600 rounded transition-colors"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                        <button
                          onClick={e => { e.stopPropagation(); navigate(`/workspaces/${workspaceId}/content/${item.id}`); }}
                          className="p-1 hover:bg-indigo-50 text-slate-400 hover:text-indigo-600 rounded transition-colors"
                        >
                          <Info className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={e => { e.stopPropagation(); setDeleteConfirmId(item.id); }}
                          className="p-1 hover:bg-red-50 text-slate-400 hover:text-red-500 rounded transition-colors"
                          title="Delete content item"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100 bg-slate-50/50">
              <span className="text-xs text-slate-500 tabular-nums">
                Page {page} of {totalPages} &middot; {sorted.length} items
              </span>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1.5 text-xs font-medium text-slate-600 bg-white border border-slate-200 rounded-md hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-3 py-1.5 text-xs font-medium text-slate-600 bg-white border border-slate-200 rounded-md hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ---- Delete Confirmation Dialog ---- */}
      {deleteConfirmId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" onClick={() => setDeleteConfirmId(null)} />
          <div className="relative w-full max-w-md bg-white rounded-2xl shadow-2xl p-6 space-y-4">
            <div className="flex items-center gap-3 text-red-600">
              <AlertCircle className="w-6 h-6" />
              <h3 className="text-lg font-bold text-slate-900">Delete Content Item</h3>
            </div>
            <p className="text-sm text-slate-600">
              This will permanently delete this content item. This action cannot be undone.
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
