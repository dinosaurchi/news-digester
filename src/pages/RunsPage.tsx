import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useParams } from 'react-router-dom';
import {
  Play, Info, Activity, ChevronDown, ChevronUp, ChevronRight,
  AlertTriangle, FileText, CheckCircle2, XCircle, Loader2,
  ArrowUpDown, ExternalLink,
} from 'lucide-react';
import { formatDate, formatDuration, cn } from '@/lib/utils';
import { useState, useMemo } from 'react';
import { PageHeader } from '@/components/ui/page-header';
import { StatusBadge } from '@/components/ui/status-badge';
import { EmptyState } from '@/components/ui/empty-state';
import { Sheet } from '@/components/ui/sheet';
import { Skeleton } from '@/components/ui/loading-skeleton';
import { StepTimeline } from '@/components/ui/step-timeline';
import type { RunType, RunStatus, RunDetail } from '@/lib/types';
import type { RunFilters } from '@/types';

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

type DatePreset = 'all' | 'today' | '7d' | '30d';

const PAGE_SIZE = 10;

type SortKey = 'startedAt' | 'durationMs' | 'status' | 'type';
type SortDir = 'asc' | 'desc';

const datePresets: { value: DatePreset; label: string }[] = [
  { value: 'all', label: 'All time' },
  { value: 'today', label: 'Today' },
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function getDateRange(preset: DatePreset): Partial<Pick<RunFilters, 'dateFrom' | 'dateTo'>> {
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

function RunsTableSkeleton() {
  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse min-w-[960px]">
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
            {Array.from({ length: 6 }).map((_, i) => (
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
/*  RunsPage                                                           */
/* ================================================================== */

export default function RunsPage() {
  const params = useParams();
  const workspaceId = params.workspaceId as string;
  const queryClient = useQueryClient();

  /* ---- filter state ---- */
  const [typeFilter, setTypeFilter] = useState<RunType | 'all'>('all');
  const [statusFilter, setStatusFilter] = useState<RunStatus | 'all'>('all');
  const [datePreset, setDatePreset] = useState<DatePreset>('all');

  /* ---- sort state ---- */
  const [sortKey, setSortKey] = useState<SortKey>('startedAt');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  /* ---- pagination ---- */
  const [page, setPage] = useState(1);

  /* ---- detail drawer ---- */
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [expandedErrors, setExpandedErrors] = useState<Set<string>>(new Set());

  /* ---- computed filters ---- */
  const filters: RunFilters = useMemo(() => {
    const dr = getDateRange(datePreset);
    return {
      ...(typeFilter !== 'all' ? { type: typeFilter } : {}),
      ...(statusFilter !== 'all' ? { status: statusFilter } : {}),
      ...dr,
    };
  }, [typeFilter, statusFilter, datePreset]);

  const hasActiveFilters = typeFilter !== 'all' || statusFilter !== 'all' || datePreset !== 'all';

  const clearFilters = () => {
    setTypeFilter('all');
    setStatusFilter('all');
    setDatePreset('all');
    setPage(1);
  };

  /* ---- data ---- */
  const { data: runs, isLoading } = useQuery({
    queryKey: ['runs', workspaceId, filters],
    queryFn: () => api.runs.list(workspaceId, filters),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;
      return (data as Array<{ status: string }>).some(r => r.status === 'running') ? 3000 : false;
    },
  });

  const { data: detail, isLoading: detailLoading } = useQuery({
    queryKey: ['run-detail', selectedId],
    queryFn: () => api.runs.getDetail(selectedId!),
    enabled: !!selectedId,
  });

  /* ---- trigger mutation ---- */
  const triggerMutation = useMutation({
    mutationFn: () => api.runs.trigger(workspaceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['runs', workspaceId] });
    },
  });

  /* ---- sort ---- */
  const sorted = useMemo(() => {
    if (!runs) return [];
    return [...runs].sort((a, b) => {
      let av: string | number | undefined;
      let bv: string | number | undefined;
      if (sortKey === 'durationMs') {
        av = a.durationMs ?? -1;
        bv = b.durationMs ?? -1;
      } else {
        av = a[sortKey];
        bv = b[sortKey];
      }
      if (typeof av === 'string' && typeof bv === 'string') {
        return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      if (typeof av === 'number' && typeof bv === 'number') {
        return sortDir === 'asc' ? av - bv : bv - av;
      }
      return 0;
    });
  }, [runs, sortKey, sortDir]);

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

  const toggleError = (id: string) => {
    setExpandedErrors(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  /* ---- loading ---- */
  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Operational Runs" description="Monitor intelligence cycle execution and system logs." />
        <Skeleton className="h-14 w-full rounded-xl" />
        <RunsTableSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ---- Header ---- */}
      <PageHeader
        title="Operational Runs"
        description="Monitor intelligence cycle execution and system logs."
        actions={
          <button
            onClick={() => triggerMutation.mutate()}
            disabled={triggerMutation.isPending}
            className={cn(
              'flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium text-sm transition-colors shadow-sm',
              triggerMutation.isPending
                ? 'bg-slate-300 text-slate-500 cursor-not-allowed'
                : 'bg-indigo-600 hover:bg-indigo-700 text-white',
            )}
          >
            {triggerMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4 fill-current" />
            )}
            {triggerMutation.isPending ? 'Triggering…' : 'Trigger Manual Run'}
          </button>
        }
      />

      {/* ---- Filter Bar ---- */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-4">
        <div className="flex flex-wrap items-center gap-3">
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

          <select
            value={typeFilter}
            onChange={e => { setTypeFilter(e.target.value as RunType | 'all'); setPage(1); }}
            className="text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
          >
            <option value="all">All Types</option>
            <option value="scheduled">Scheduled</option>
            <option value="manual">Manual</option>
          </select>

          <select
            value={statusFilter}
            onChange={e => { setStatusFilter(e.target.value as RunStatus | 'all'); setPage(1); }}
            className="text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
          >
            <option value="all">All Statuses</option>
            <option value="success">Success</option>
            <option value="failed">Failed</option>
            <option value="running">Running</option>
          </select>

          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-500 hover:text-red-600 border border-slate-200 hover:border-red-200 rounded-lg transition-colors"
            >
              Clear filters
            </button>
          )}

          <span className="ml-auto text-xs text-slate-400 tabular-nums">
            {sorted.length} run{sorted.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      {/* ---- Table or Empty ---- */}
      {sorted.length === 0 ? (
        <EmptyState
          icon={Activity}
          title="No runs found"
          description={
            hasActiveFilters
              ? 'Try adjusting your filters to see more results.'
              : 'No runs have been executed yet. Trigger a manual run to get started.'
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
            <table className="w-full text-left border-collapse min-w-[960px]">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <SortableTh label="Run ID" column="startedAt" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} className="min-w-[120px]" />
                  <SortableTh label="Type" column="type" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                  <SortableTh label="Status" column="status" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                  <SortableTh label="Started" column="startedAt" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                  <SortableTh label="Duration" column="durationMs" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                  <th className="px-3 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Feeds</th>
                  <th className="px-3 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Articles</th>
                  <th className="px-3 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Reports</th>
                  <th className="px-3 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Error</th>
                  <th className="px-3 py-2.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {paged.map(run => {
                  const isExpanded = expandedErrors.has(run.id);
                  const hasError = !!run.error;

                  return (
                    <tr
                      key={run.id}
                      className={cn(
                        'hover:bg-slate-50/70 transition-colors cursor-pointer group',
                        run.status === 'failed' && 'bg-red-50/30',
                      )}
                      onClick={() => setSelectedId(run.id)}
                    >
                      {/* Run ID */}
                      <td className="px-3 py-2.5">
                        <span className="text-xs font-mono text-slate-600">#{run.id}</span>
                      </td>
                      {/* Type */}
                      <td className="px-3 py-2.5">
                        <StatusBadge
                          status={run.type}
                          label={run.type === 'scheduled' ? 'Scheduled' : 'Manual'}
                        />
                      </td>
                      {/* Status */}
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-1.5">
                          {run.status === 'success' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />}
                          {run.status === 'failed' && <XCircle className="w-3.5 h-3.5 text-red-500" />}
                          {run.status === 'running' && <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin" />}
                          <StatusBadge status={run.status} />
                        </div>
                      </td>
                      {/* Started At */}
                      <td className="px-3 py-2.5">
                        <span className="text-xs text-slate-500 tabular-nums">{formatDate(run.startedAt)}</span>
                      </td>
                      {/* Duration */}
                      <td className="px-3 py-2.5">
                        <span className={cn(
                          'text-xs tabular-nums',
                          run.status === 'running' ? 'text-blue-500 font-medium' : 'text-slate-500',
                        )}>
                          {run.status === 'running' ? 'Running…' : formatDuration(run.durationMs)}
                        </span>
                      </td>
                      {/* Feeds */}
                      <td className="px-3 py-2.5">
                        <span className="text-xs text-slate-600 tabular-nums font-medium">{run.affectedCounts.feeds}</span>
                      </td>
                      {/* Articles */}
                      <td className="px-3 py-2.5">
                        <span className="text-xs text-slate-600 tabular-nums font-medium">{run.affectedCounts.articles}</span>
                      </td>
                      {/* Reports */}
                      <td className="px-3 py-2.5">
                        <span className="text-xs text-slate-600 tabular-nums font-medium">{run.affectedCounts.reports}</span>
                      </td>
                      {/* Error */}
                      <td className="px-3 py-2.5 max-w-[200px]">
                        {hasError ? (
                          <button
                            onClick={e => { e.stopPropagation(); toggleError(run.id); }}
                            className="flex items-center gap-1 text-xs text-red-600 hover:text-red-700 transition-colors"
                          >
                            <AlertTriangle className="w-3 h-3 shrink-0" />
                            <span className={cn('truncate', !isExpanded && 'max-w-[140px]')}>
                              {isExpanded ? run.error : run.error!.length > 40 ? run.error!.slice(0, 40) + '…' : run.error}
                            </span>
                            <ChevronRight className={cn('w-3 h-3 shrink-0 transition-transform', isExpanded && 'rotate-90')} />
                          </button>
                        ) : (
                          <span className="text-slate-300">—</span>
                        )}
                      </td>
                      {/* Actions */}
                      <td className="px-3 py-2.5 text-right">
                        <button
                          onClick={e => { e.stopPropagation(); setSelectedId(run.id); }}
                          className="p-1 hover:bg-indigo-50 text-slate-400 hover:text-indigo-600 rounded transition-colors"
                        >
                          <Info className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100 bg-slate-50/50">
              <span className="text-xs text-slate-500 tabular-nums">
                Page {page} of {totalPages} &middot; {sorted.length} runs
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

      {/* ---- Detail Drawer ---- */}
      <RunDetailSheet
        open={!!selectedId}
        onClose={() => setSelectedId(null)}
        detail={detail}
        loading={detailLoading}
      />
    </div>
  );
}

/* ================================================================== */
/*  Run Detail Sheet                                                   */
/* ================================================================== */

function RunDetailSheet({
  open,
  onClose,
  detail,
  loading,
}: {
  open: boolean;
  onClose: () => void;
  detail?: RunDetail;
  loading: boolean;
}) {
  const [logsExpanded, setLogsExpanded] = useState(false);

  if (!open) return null;

  // Reset logs expanded when detail changes
  const accentBorder =
    detail?.status === 'success'
      ? 'border-l-4 border-l-emerald-500'
      : detail?.status === 'failed'
        ? 'border-l-4 border-l-red-500'
        : detail?.status === 'running'
          ? 'border-l-4 border-l-blue-500'
          : '';

  return (
    <Sheet
      open={open}
      onOpenChange={onClose}
      title={detail ? `Run #${detail.id}` : 'Run Detail'}
      description={detail ? `${detail.type === 'scheduled' ? 'Scheduled' : 'Manual'} run` : undefined}
      className={accentBorder}
    >
      {loading || !detail ? (
        <div className="space-y-5">
          <Skeleton className="h-5 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Header badges */}
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={detail.status} size="md" />
            <StatusBadge
              status={detail.type}
              label={detail.type === 'scheduled' ? 'Scheduled' : 'Manual'}
              size="md"
            />
          </div>

          {/* Error banner (prominent) */}
          {detail.error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 space-y-1">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-red-500" />
                <span className="text-xs font-bold text-red-700 uppercase tracking-wider">Run Failed</span>
              </div>
              <p className="text-sm text-red-800">{detail.error}</p>
            </div>
          )}

          {/* Timing Info */}
          <section className="space-y-2.5">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Timing</h3>
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-slate-50 rounded-lg p-3 text-center">
                <p className="text-[10px] font-bold text-slate-400 uppercase">Started</p>
                <p className="text-xs text-slate-700 mt-0.5 tabular-nums">{formatDate(detail.startedAt)}</p>
              </div>
              <div className="bg-slate-50 rounded-lg p-3 text-center">
                <p className="text-[10px] font-bold text-slate-400 uppercase">Completed</p>
                <p className="text-xs text-slate-700 mt-0.5 tabular-nums">
                  {detail.completedAt ? formatDate(detail.completedAt) : '—'}
                </p>
              </div>
              <div className="bg-slate-50 rounded-lg p-3 text-center">
                <p className="text-[10px] font-bold text-slate-400 uppercase">Duration</p>
                <p className={cn(
                  'text-xs font-bold mt-0.5 tabular-nums',
                  detail.status === 'running' ? 'text-blue-600' : 'text-slate-700',
                )}>
                  {detail.status === 'running' ? 'Running…' : formatDuration(detail.durationMs)}
                </p>
              </div>
            </div>
          </section>

          {/* Affected Counts */}
          <section className="space-y-2.5">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Impact</h3>
            <div className="flex items-center gap-4">
              <ImpactPill label="Feeds" value={detail.affectedCounts.feeds} />
              <ImpactPill label="Articles" value={detail.affectedCounts.articles} />
              <ImpactPill label="Reports" value={detail.affectedCounts.reports} />
            </div>
          </section>

          {/* Step Timeline */}
          <section className="space-y-2.5">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Step Timeline</h3>
            <div className="bg-slate-50/50 rounded-lg p-4 border border-slate-200">
              {detail.steps.length > 0 ? (
                <StepTimeline steps={detail.steps} />
              ) : (
                <p className="text-xs text-slate-400">No step data available.</p>
              )}
            </div>
          </section>

          {/* Log Snippets */}
          {detail.logSnippets.length > 0 && (
            <section className="space-y-2">
              <button
                onClick={() => setLogsExpanded(!logsExpanded)}
                className="flex items-center gap-1.5 text-xs font-bold text-slate-400 uppercase tracking-wider hover:text-slate-600 transition-colors"
              >
                <ChevronRight className={cn('w-3 h-3 transition-transform', logsExpanded && 'rotate-90')} />
                Log Snippets ({detail.logSnippets.length})
              </button>
              {logsExpanded && (
                <div className="bg-slate-900 rounded-lg p-4 font-mono text-xs leading-relaxed max-h-64 overflow-y-auto">
                  {detail.logSnippets.map((line, i) => (
                    <div
                      key={i}
                      className={cn(
                        line.startsWith('[ERROR]')
                          ? 'text-red-400'
                          : line.startsWith('[WARN]')
                            ? 'text-amber-400'
                            : 'text-slate-300',
                      )}
                    >
                      {line}
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}

          {/* Linked Items */}
          {(detail.links.reports?.length || detail.links.contentItems?.length) ? (
            <section className="space-y-2.5">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Generated Items</h3>
              <div className="space-y-2">
                {detail.links.reports && detail.links.reports.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {detail.links.reports.map(id => (
                      <span
                        key={id}
                        className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 bg-indigo-50 border border-indigo-200 rounded-md px-2.5 py-1"
                      >
                        <FileText className="w-3 h-3" />
                        {id}
                      </span>
                    ))}
                  </div>
                )}
                {detail.links.contentItems && detail.links.contentItems.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {detail.links.contentItems.slice(0, 5).map(id => (
                      <span
                        key={id}
                        className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 bg-slate-50 border border-slate-200 rounded-md px-2.5 py-1"
                      >
                        <ExternalLink className="w-3 h-3" />
                        {id}
                      </span>
                    ))}
                    {detail.links.contentItems.length > 5 && (
                      <span className="text-xs text-slate-400">
                        +{detail.links.contentItems.length - 5} more
                      </span>
                    )}
                  </div>
                )}
              </div>
            </section>
          ) : null}
        </div>
      )}
    </Sheet>
  );
}

/* ------------------------------------------------------------------ */
/*  Tiny helpers                                                       */
/* ------------------------------------------------------------------ */

function ImpactPill({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex-1 bg-slate-50 rounded-lg px-3 py-2 text-center border border-slate-100">
      <p className="text-[10px] font-bold text-slate-400 uppercase">{label}</p>
      <p className="text-lg font-bold text-slate-800 tabular-nums">{value}</p>
    </div>
  );
}
