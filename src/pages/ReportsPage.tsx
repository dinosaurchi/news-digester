import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useParams } from 'react-router-dom';
import { Link } from 'react-router-dom';
import {
  MessageSquare,
  Calendar,
  Search,
  Filter,
  Clock,
  Hash,
  ArrowRight,
  X,
} from 'lucide-react';
import { formatDateRange, timeAgo, cn } from '@/lib/utils';
import { PageHeader } from '@/components/ui/page-header';
import { StatusBadge } from '@/components/ui/status-badge';
import { Skeleton, CardSkeleton } from '@/components/ui/loading-skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import type { ReportStatus } from '@/types';

type StatusFilter = 'all' | ReportStatus;
type DateFilter = 'all' | '7d' | '30d' | '90d';

const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: 'all', label: 'All Statuses' },
  { value: 'published', label: 'Published' },
  { value: 'draft', label: 'Draft' },
  { value: 'archived', label: 'Archived' },
];

const DATE_OPTIONS: { value: DateFilter; label: string }[] = [
  { value: 'all', label: 'All Time' },
  { value: '7d', label: 'Last 7 Days' },
  { value: '30d', label: 'Last 30 Days' },
  { value: '90d', label: 'Last 90 Days' },
];

export default function ReportsPage() {
  const params = useParams();
  const workspaceId = params.workspaceId as string;

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [dateFilter, setDateFilter] = useState<DateFilter>('all');
  const [showStatusDropdown, setShowStatusDropdown] = useState(false);
  const [showDateDropdown, setShowDateDropdown] = useState(false);

  const { data: reports, isLoading } = useQuery({
    queryKey: ['reports', workspaceId],
    queryFn: () => api.reports.list(workspaceId),
  });

  const now = Date.now();
  const dateCutoff = useMemo(() => {
    switch (dateFilter) {
      case '7d': return now - 7 * 24 * 60 * 60 * 1000;
      case '30d': return now - 30 * 24 * 60 * 60 * 1000;
      case '90d': return now - 90 * 24 * 60 * 60 * 1000;
      default: return 0;
    }
  }, [dateFilter, now]);

  const filteredReports = useMemo(() => {
    if (!reports) return [];
    return reports.filter((r) => {
      if (statusFilter !== 'all' && r.status !== statusFilter) return false;
      if (dateFilter !== 'all' && new Date(r.createdAt).getTime() < dateCutoff) return false;
      if (search.trim()) {
        const q = search.toLowerCase();
        if (
          !r.title.toLowerCase().includes(q) &&
          !r.runId.toLowerCase().includes(q) &&
          !(r.latestHighlight || '').toLowerCase().includes(q)
        )
          return false;
      }
      return true;
    });
  }, [reports, statusFilter, dateFilter, dateCutoff, search]);

  const hasActiveFilters = statusFilter !== 'all' || dateFilter !== 'all' || search.trim().length > 0;

  const clearFilters = () => {
    setStatusFilter('all');
    setDateFilter('all');
    setSearch('');
  };

  if (isLoading) {
    return (
      <div className="space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-8 w-56 mb-2" />
            <Skeleton className="h-4 w-80" />
          </div>
        </div>
        <div className="flex gap-3">
          <Skeleton className="h-10 w-72 rounded-xl" />
          <Skeleton className="h-10 w-36 rounded-xl" />
          <Skeleton className="h-10 w-36 rounded-xl" />
        </div>
        <div className="space-y-4">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <PageHeader
        title="Intelligence Reports"
        description="Conversational report threads — review, discuss, and refine intelligence with your AI analyst."
      />

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Search */}
        <div className="relative flex-1 min-w-[240px] max-w-md">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search threads by title..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 transition-shadow"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 hover:bg-slate-100 rounded-md text-slate-400 transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Status Filter */}
        <div className="relative">
          <button
            onClick={() => { setShowStatusDropdown(!showStatusDropdown); setShowDateDropdown(false); }}
            className="flex items-center gap-2 px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors"
          >
            <Filter className="w-4 h-4" />
            {STATUS_OPTIONS.find((o) => o.value === statusFilter)?.label || 'Status'}
            {statusFilter !== 'all' && (
              <span className="w-2 h-2 bg-indigo-500 rounded-full" />
            )}
          </button>
          {showStatusDropdown && (
            <div className="absolute top-full left-0 mt-1 w-48 bg-white border border-slate-200 rounded-xl shadow-lg z-20 py-1">
              {STATUS_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => { setStatusFilter(opt.value); setShowStatusDropdown(false); }}
                  className={cn(
                    'w-full text-left px-4 py-2 text-sm transition-colors',
                    statusFilter === opt.value
                      ? 'bg-indigo-50 text-indigo-700 font-medium'
                      : 'text-slate-600 hover:bg-slate-50'
                  )}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Date Filter */}
        <div className="relative">
          <button
            onClick={() => { setShowDateDropdown(!showDateDropdown); setShowStatusDropdown(false); }}
            className="flex items-center gap-2 px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors"
          >
            <Calendar className="w-4 h-4" />
            {DATE_OPTIONS.find((o) => o.value === dateFilter)?.label || 'Date'}
            {dateFilter !== 'all' && (
              <span className="w-2 h-2 bg-indigo-500 rounded-full" />
            )}
          </button>
          {showDateDropdown && (
            <div className="absolute top-full left-0 mt-1 w-48 bg-white border border-slate-200 rounded-xl shadow-lg z-20 py-1">
              {DATE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => { setDateFilter(opt.value); setShowDateDropdown(false); }}
                  className={cn(
                    'w-full text-left px-4 py-2 text-sm transition-colors',
                    dateFilter === opt.value
                      ? 'bg-indigo-50 text-indigo-700 font-medium'
                      : 'text-slate-600 hover:bg-slate-50'
                  )}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Active Filters Clear */}
        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="flex items-center gap-1.5 px-3 py-2.5 text-sm text-slate-500 hover:text-slate-700 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
            Clear filters
          </button>
        )}
      </div>

      {/* Results count */}
      {reports && reports.length > 0 && (
        <p className="text-xs text-slate-400 font-medium">
          Showing {filteredReports.length} of {reports.length} threads
        </p>
      )}

      {/* Thread List */}
      <div className="space-y-3">
        {filteredReports.map((thread) => (
          <Link
            key={thread.id}
            to={`/workspaces/${workspaceId}/reports/${thread.id}`}
            className="group block bg-white border border-slate-200 rounded-xl p-5 hover:border-indigo-300 hover:shadow-md transition-all duration-200"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-4 flex-1 min-w-0">
                {/* Icon */}
                <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-600 flex items-center justify-center text-white shrink-0 shadow-sm group-hover:shadow-indigo-200 group-hover:shadow-md transition-shadow">
                  <MessageSquare className="w-5 h-5" />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  {/* Title row */}
                  <div className="flex items-center gap-3 mb-1.5">
                    <h3 className="text-[15px] font-semibold text-slate-900 truncate group-hover:text-indigo-600 transition-colors">
                      {thread.title}
                    </h3>
                    <StatusBadge status={thread.status} />
                  </div>

                  {/* Meta row */}
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 mb-2">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      {formatDateRange(thread.periodStart, thread.periodEnd)}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-slate-400" />
                      {timeAgo(thread.createdAt)}
                    </span>
                    <span className="flex items-center gap-1 font-mono text-slate-400">
                      <Hash className="w-3.5 h-3.5" />
                      {thread.runId}
                    </span>
                    <span className="flex items-center gap-1">
                      <MessageSquare className="w-3.5 h-3.5 text-slate-400" />
                      {thread.messageCount} {thread.messageCount === 1 ? 'message' : 'messages'}
                    </span>
                  </div>

                  {/* Excerpt */}
                  {thread.latestHighlight && (
                    <p className="text-sm text-slate-500 leading-relaxed line-clamp-1">
                      {thread.latestHighlight}
                    </p>
                  )}
                </div>
              </div>

              {/* CTA */}
              <div className="flex items-center shrink-0 pt-1">
                <span className="flex items-center gap-1 text-sm font-medium text-indigo-600 opacity-0 group-hover:opacity-100 transition-opacity">
                  Open Thread
                  <ArrowRight className="w-4 h-4" />
                </span>
              </div>
            </div>
          </Link>
        ))}

        {/* Empty state: no results with filters */}
        {reports && reports.length > 0 && filteredReports.length === 0 && (
          <div className="py-12 text-center">
            <div className="w-14 h-14 bg-slate-100 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Search className="w-7 h-7 text-slate-400" />
            </div>
            <h3 className="text-base font-semibold text-slate-900 mb-1">No matching threads</h3>
            <p className="text-sm text-slate-500 mb-4">Try adjusting your search or filter criteria.</p>
            <button
              onClick={clearFilters}
              className="text-sm font-medium text-indigo-600 hover:text-indigo-700 transition-colors"
            >
              Clear all filters
            </button>
          </div>
        )}

        {/* Empty state: no reports at all */}
        {reports && reports.length === 0 && (
          <EmptyState
            icon={MessageSquare}
            title="No reports yet"
            description="Intelligence report threads will appear here once the monitoring cycle runs and generates reports."
          />
        )}
      </div>
    </div>
  );
}
