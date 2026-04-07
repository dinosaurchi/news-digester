import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useParams, Link } from 'react-router-dom';
import {
  ThumbsUp,
  ThumbsDown,
  MessageSquare,
  Target,
  Globe,
  TrendingUp,
  TrendingDown,
  FileText,
  ArrowUpRight,
  Sparkles,
  BarChart3,
  AlertCircle,
  RotateCcw,
} from 'lucide-react';
import { cn, timeAgo } from '@/lib/utils';
import { PageHeader } from '@/components/ui/page-header';
import { EmptyState } from '@/components/ui/empty-state';
import { StatCardSkeleton, Skeleton } from '@/components/ui/loading-skeleton';
import type { FeedbackEvent, FeedbackEventType } from '@/lib/types';

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

type EventTypeFilter = 'all' | FeedbackEventType;

const EVENT_TYPE_FILTERS: { value: EventTypeFilter; label: string; icon: React.ElementType }[] = [
  { value: 'all', label: 'All', icon: BarChart3 },
  { value: 'thumbs_up', label: 'Thumbs Up', icon: ThumbsUp },
  { value: 'thumbs_down', label: 'Thumbs Down', icon: ThumbsDown },
  { value: 'comment', label: 'Comments', icon: MessageSquare },
  { value: 'topic_preference', label: 'Topics', icon: Target },
  { value: 'source_preference', label: 'Sources', icon: Globe },
];

const TYPE_CONFIG: Record<FeedbackEventType, { icon: React.ElementType; bg: string; color: string; label: string; badgeBg: string; badgeColor: string; badgeBorder: string }> = {
  thumbs_up: {
    icon: ThumbsUp,
    bg: 'bg-emerald-50',
    color: 'text-emerald-600',
    label: 'Thumbs Up',
    badgeBg: 'bg-emerald-50',
    badgeColor: 'text-emerald-700',
    badgeBorder: 'border-emerald-200',
  },
  thumbs_down: {
    icon: ThumbsDown,
    bg: 'bg-red-50',
    color: 'text-red-600',
    label: 'Thumbs Down',
    badgeBg: 'bg-red-50',
    badgeColor: 'text-red-700',
    badgeBorder: 'border-red-200',
  },
  comment: {
    icon: MessageSquare,
    bg: 'bg-blue-50',
    color: 'text-blue-600',
    label: 'Comment',
    badgeBg: 'bg-blue-50',
    badgeColor: 'text-blue-700',
    badgeBorder: 'border-blue-200',
  },
  topic_preference: {
    icon: Target,
    bg: 'bg-indigo-50',
    color: 'text-indigo-600',
    label: 'Topic',
    badgeBg: 'bg-indigo-50',
    badgeColor: 'text-indigo-700',
    badgeBorder: 'border-indigo-200',
  },
  source_preference: {
    icon: Globe,
    bg: 'bg-amber-50',
    color: 'text-amber-600',
    label: 'Source',
    badgeBg: 'bg-amber-50',
    badgeColor: 'text-amber-700',
    badgeBorder: 'border-amber-200',
  },
};

const SENTIMENT_STYLES: Record<string, { bg: string; bar: string; label: string }> = {
  positive: { bg: 'bg-emerald-50 text-emerald-700 border-emerald-200', bar: 'bg-emerald-500', label: 'Boosted' },
  negative: { bg: 'bg-red-50 text-red-700 border-red-200', bar: 'bg-red-500', label: 'Suppressed' },
  neutral: { bg: 'bg-slate-50 text-slate-600 border-slate-200', bar: 'bg-slate-400', label: 'Neutral' },
};

const STYLE_LABELS: Record<string, string> = {
  detailed: 'Detailed',
  concise: 'Concise',
  bulleted: 'Bullet Points',
};

/* ================================================================== */
/*  FeedbackPage                                                        */
/* ================================================================== */

export default function FeedbackPage() {
  const params = useParams();
  const workspaceId = params.workspaceId as string;
  const [typeFilter, setTypeFilter] = useState<EventTypeFilter>('all');

  const { data: events, isLoading: eventsLoading, error: eventsError, refetch: refetchEvents } = useQuery({
    queryKey: ['feedback', workspaceId],
    queryFn: () => api.feedback.list(workspaceId),
  });

  const { data: summary, isLoading: summaryLoading, error: summaryError, refetch: refetchSummary } = useQuery({
    queryKey: ['feedback-summary', workspaceId],
    queryFn: () => api.feedback.getSummary(workspaceId),
  });

  const filteredEvents = useMemo(() => {
    if (!events) return [];
    if (typeFilter === 'all') return events;
    return events.filter(e => e.type === typeFilter);
  }, [events, typeFilter]);

  const isLoading = eventsLoading || summaryLoading;
  const hasError = eventsError || summaryError;

  /* ---- Loading ---- */
  if (isLoading) {
    return (
      <div className="space-y-8">
        <div className="h-8 w-64 bg-slate-200 animate-pulse rounded" />
        <div className="h-4 w-96 bg-slate-200 animate-pulse rounded" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => <StatCardSkeleton key={i} />)}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <Skeleton className="h-10 w-full rounded-xl" />
            <div className="space-y-3">
              {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-28 w-full rounded-xl" />)}
            </div>
          </div>
          <div className="space-y-6">
            <Skeleton className="h-56 w-full rounded-xl" />
            <Skeleton className="h-56 w-full rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  /* ---- Error ---- */
  if (hasError) {
    return (
      <div className="space-y-8">
        <PageHeader title="Feedback & Preferences" description="Analyze captured feedback and how it influences intelligence tuning." />
        <div className="bg-red-50 border border-red-200 rounded-xl p-8 text-center">
          <div className="w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-6 h-6 text-red-500" />
          </div>
          <p className="text-sm font-semibold text-red-800 mb-1">Failed to load feedback data</p>
          <p className="text-xs text-red-600 mb-4">There was an error fetching feedback for this workspace.</p>
          <button
            onClick={() => { refetchEvents(); refetchSummary(); }}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Feedback & Preferences"
        description="Analyze captured feedback and how it influences intelligence tuning."
      />

      {/* ---- Summary Stat Cards ---- */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryStatCard
          title="Total Feedback Events"
          value={summary?.totalEvents ?? 0}
          icon={BarChart3}
          iconBg="bg-slate-100"
          iconColor="text-slate-600"
        />
        <SummaryStatCard
          title="Thumbs Up"
          value={summary?.thumbsUp ?? 0}
          subtitle={summary && summary.totalEvents > 0
            ? `${Math.round((summary.thumbsUp / summary.totalEvents) * 100)}% of all events`
            : undefined}
          icon={ThumbsUp}
          iconBg="bg-emerald-50"
          iconColor="text-emerald-600"
          valueColor="text-emerald-600"
        />
        <SummaryStatCard
          title="Thumbs Down"
          value={summary?.thumbsDown ?? 0}
          subtitle={summary && summary.totalEvents > 0
            ? `${Math.round((summary.thumbsDown / summary.totalEvents) * 100)}% of all events`
            : undefined}
          icon={ThumbsDown}
          iconBg="bg-red-50"
          iconColor="text-red-600"
          valueColor="text-red-600"
        />
        <SummaryStatCard
          title="Net Sentiment"
          value={summary ? (summary.netSentiment >= 0 ? `+${summary.netSentiment}` : `${summary.netSentiment}`) : '0'}
          subtitle="Thumbs up minus thumbs down"
          icon={summary && summary.netSentiment >= 0 ? TrendingUp : TrendingDown}
          iconBg={summary && summary.netSentiment >= 0 ? 'bg-emerald-50' : 'bg-red-50'}
          iconColor={summary && summary.netSentiment >= 0 ? 'text-emerald-600' : 'text-red-600'}
          valueColor={summary && summary.netSentiment >= 0 ? 'text-emerald-600' : 'text-red-600'}
        />
      </div>

      {/* ---- Main Content ---- */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Feedback Timeline */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-slate-900">Feedback Timeline</h3>
            <span className="text-xs text-slate-400 tabular-nums">
              {filteredEvents.length} event{filteredEvents.length !== 1 ? 's' : ''}
            </span>
          </div>

          {/* Type Filter Pills */}
          <div className="flex flex-wrap items-center gap-1.5">
            {EVENT_TYPE_FILTERS.map(f => (
              <button
                key={f.value}
                onClick={() => setTypeFilter(f.value)}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
                  typeFilter === f.value
                    ? 'bg-indigo-100 text-indigo-700'
                    : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                )}
              >
                <f.icon className="w-3 h-3" />
                {f.label}
              </button>
            ))}
          </div>

          {/* Events List */}
          {filteredEvents.length === 0 ? (
            <EmptyState
              icon={MessageSquare}
              title="No feedback events"
              description={
                typeFilter !== 'all'
                  ? 'No events match this filter. Try selecting a different type.'
                  : 'No feedback has been captured yet. Interact with reports to generate feedback.'
              }
            />
          ) : (
            <div className="space-y-3">
              {filteredEvents.map(event => (
                <FeedbackEventCard key={event.id} event={event} workspaceId={workspaceId} />
              ))}
            </div>
          )}
        </div>

        {/* Right: Preferences Panels */}
        <div className="space-y-6">
          {/* Topic Preferences */}
          {summary && summary.topicPreferences.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-indigo-50 rounded-md">
                  <Target className="w-3.5 h-3.5 text-indigo-600" />
                </div>
                <h3 className="text-sm font-bold text-slate-900">Topic Preferences</h3>
              </div>
              <div className="space-y-3">
                {summary.topicPreferences.map(tp => (
                  <PreferenceRow key={tp.topic} label={tp.topic} count={tp.count} sentiment={tp.sentiment} />
                ))}
              </div>
            </div>
          )}

          {/* Source Preferences */}
          {summary && summary.sourcePreferences.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-amber-50 rounded-md">
                  <Globe className="w-3.5 h-3.5 text-amber-600" />
                </div>
                <h3 className="text-sm font-bold text-slate-900">Source Preferences</h3>
              </div>
              <div className="space-y-3">
                {summary.sourcePreferences.map(sp => (
                  <PreferenceRow key={sp.source} label={sp.source} count={sp.count} sentiment={sp.sentiment} />
                ))}
              </div>
            </div>
          )}

          {/* Report Style Preferences */}
          {summary && summary.reportStylePreferences.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-violet-50 rounded-md">
                  <FileText className="w-3.5 h-3.5 text-violet-600" />
                </div>
                <h3 className="text-sm font-bold text-slate-900">Report Style Preferences</h3>
              </div>
              <div className="space-y-3">
                {summary.reportStylePreferences
                  .sort((a, b) => b.count - a.count)
                  .map(rs => {
                    const maxCount = Math.max(...summary.reportStylePreferences.map(r => r.count));
                    return (
                      <div key={rs.style} className="flex items-center justify-between gap-3">
                        <span className="text-sm text-slate-700">{STYLE_LABELS[rs.style] || rs.style}</span>
                        <div className="flex items-center gap-3">
                          <div className="w-24 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-violet-500 rounded-full transition-all duration-300"
                              style={{ width: `${maxCount > 0 ? (rs.count / maxCount) * 100 : 0}%` }}
                            />
                          </div>
                          <span className="text-xs font-bold text-slate-600 tabular-nums w-6 text-right">{rs.count}</span>
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ================================================================== */
/*  Sub-components                                                     */
/* ================================================================== */

function SummaryStatCard({
  title, value, subtitle, icon: Icon, iconBg, iconColor, valueColor,
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ElementType;
  iconBg: string;
  iconColor: string;
  valueColor?: string;
}) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{title}</p>
        <div className={cn('p-2 rounded-lg', iconBg, iconColor)}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <p className={cn('text-2xl font-bold leading-tight', valueColor || 'text-slate-900')}>{value}</p>
      {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
    </div>
  );
}

function FeedbackEventCard({ event, workspaceId }: { event: FeedbackEvent; workspaceId: string }) {
  const config = TYPE_CONFIG[event.type];
  const Icon = config.icon;
  const description = getEventDescription(event);

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex gap-3.5">
        {/* Type icon */}
        <div className={cn('w-9 h-9 rounded-lg flex items-center justify-center shrink-0', config.bg, config.color)}>
          <Icon className="w-4 h-4" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0 space-y-1.5">
          {/* Description */}
          <p className="text-sm font-medium text-slate-900">{description}</p>

          {/* Report link */}
          {event.reportTitle && (
            <Link
              to={`/workspaces/${workspaceId}/reports/${event.threadId}`}
              className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-700 font-medium group/link"
            >
              <FileText className="w-3 h-3 shrink-0" />
              <span className="truncate max-w-[320px]">{event.reportTitle}</span>
              <ArrowUpRight className="w-3 h-3 shrink-0 opacity-0 group-hover/link:opacity-100 transition-opacity" />
            </Link>
          )}

          {/* Message excerpt or value */}
          {(event.messageExcerpt || event.value) && (
            <p className="text-xs text-slate-500 leading-relaxed line-clamp-2">
              &ldquo;{event.messageExcerpt || event.value}&rdquo;
            </p>
          )}

          {/* Meta row */}
          <div className="flex flex-wrap items-center gap-2 pt-0.5">
            <span className="text-[11px] text-slate-400">{timeAgo(event.createdAt)}</span>
            {/* Type badge */}
            <span className={cn(
              'inline-flex items-center px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide rounded border',
              config.badgeBg, config.badgeColor, config.badgeBorder,
            )}>
              {config.label}
            </span>
            {/* Influenced badge */}
            {event.influencedReportCount && event.influencedReportCount > 0 && (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium bg-indigo-50 text-indigo-700 rounded border border-indigo-100">
                <Sparkles className="w-2.5 h-2.5" />
                Influenced {event.influencedReportCount} report{event.influencedReportCount > 1 ? 's' : ''}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function PreferenceRow({ label, count, sentiment }: { label: string; count: number; sentiment: 'positive' | 'negative' | 'neutral' }) {
  const styles = SENTIMENT_STYLES[sentiment];
  const maxCount = 5; // visual bar max for normalization

  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm text-slate-700 truncate">{label}</span>
          <span className="text-xs font-bold text-slate-500 tabular-nums">{count}</span>
        </div>
        <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div
            className={cn('h-full rounded-full transition-all duration-300', styles.bar)}
            style={{ width: `${Math.min(100, (count / maxCount) * 100)}%` }}
          />
        </div>
      </div>
      <span className={cn(
        'shrink-0 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide rounded border',
        styles.bg,
      )}>
        {styles.label}
      </span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function getEventDescription(event: FeedbackEvent): string {
  switch (event.type) {
    case 'thumbs_up':
      return 'Thumbs up on report';
    case 'thumbs_down':
      return 'Thumbs down on report';
    case 'comment':
      return 'Commented on report';
    case 'topic_preference':
      return event.sentiment === 'negative'
        ? `Suppressed topic: ${event.value}`
        : `Boosted topic: ${event.value}`;
    case 'source_preference':
      return event.sentiment === 'negative'
        ? `Avoided source: ${event.value}`
        : `Preferred source: ${event.value}`;
    default:
      return 'Feedback event';
  }
}
