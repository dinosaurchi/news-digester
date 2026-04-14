import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ChevronLeft, FileText, Tag, Calendar, Link2, Hash,
} from 'lucide-react';
import { formatDateOnly, cn } from '@/lib/utils';
import { PageHeader } from '@/components/ui/page-header';
import { StatusBadge } from '@/components/ui/status-badge';
import { Skeleton } from '@/components/ui/loading-skeleton';
import { ScoreBar } from '@/components/ui/score-bar';
import type { ContentType } from '@/lib/types';

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

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

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

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

function MetaRow({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2">
      <Icon className="w-3.5 h-3.5 text-slate-400 mt-0.5 shrink-0" />
      <span className="text-xs font-medium text-slate-400 w-24 shrink-0">{label}</span>
      <span className="text-sm text-slate-700 min-w-0">{value}</span>
    </div>
  );
}

function ScoreRow({ label, score, bold }: { label: string; score: number; bold?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs font-medium text-slate-500 w-28 shrink-0">{label}</span>
      <div className="flex-1">
        <ScoreBar score={score} bold={bold} />
      </div>
    </div>
  );
}

/* ================================================================== */
/*  ContentDetailPage                                                  */
/* ================================================================== */

export default function ContentDetailPage() {
  const params = useParams();
  const workspaceId = params.workspaceId as string;
  const contentId = params.contentId as string;
  const navigate = useNavigate();

  const { data: detail, isLoading } = useQuery({
    queryKey: ['content-detail', contentId],
    queryFn: () => api.content.getDetail(workspaceId, contentId),
  });

  /* ---- loading ---- */
  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Content Detail" description="Loading..." />
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-6 space-y-6">
          <div className="space-y-5">
            <Skeleton className="h-5 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="space-y-6">
        <PageHeader title="Content Detail" description="Item not found." />
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-6 text-center">
          <p className="text-sm text-slate-500">The requested content item could not be loaded.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ---- Header ---- */}
      <PageHeader
        title="Content Detail"
        description={detail ? `${detail.source} · ${formatDateOnly(detail.publishedAt)}` : undefined}
        actions={
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            Back
          </button>
        }
      />

      {/* ---- Detail Card ---- */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-6 space-y-6">
        <div className="space-y-6">
          {/* Header badges */}
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={detail.status} size="md" />
            <ContentTypeBadge type={detail.type} />
          </div>

          {/* Title */}
          <h1 className="text-lg font-bold text-slate-900">{detail.title}</h1>

          {/* Metadata */}
          <section className="space-y-2.5">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Metadata</h3>
            <div className="grid grid-cols-1 gap-2 text-sm">
              <MetaRow icon={Tag} label="Source" value={detail.source} />
              <MetaRow icon={Calendar} label="Published" value={formatDateOnly(detail.publishedAt)} />
              <MetaRow
                icon={Link2}
                label="URL"
                value={
                  <a href={detail.sourceUrl} target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:underline truncate block">
                    {detail.sourceUrl}
                  </a>
                }
              />
              {detail.clusterId && (
                <MetaRow icon={Hash} label="Cluster" value={detail.clusterId} />
              )}
            </div>
          </section>

          {/* Score Breakdown */}
          <section className="space-y-2.5">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Score Breakdown</h3>
            <div className="bg-slate-50 rounded-lg p-4 space-y-3">
              <ScoreRow label="Relevance" score={detail.scoreBreakdown.relevance * 100} />
              <ScoreRow label="LLM" score={detail.scoreBreakdown.llm * 100} />
              <ScoreRow label="Freshness" score={detail.scoreBreakdown.freshness * 100} />
              <ScoreRow label="Source Authority" score={detail.scoreBreakdown.sourceAuthority * 100} />
              {detail.scoreBreakdown.feedbackAdjustment != null && (
                <ScoreRow label="Feedback Adj." score={detail.scoreBreakdown.feedbackAdjustment * 100} />
              )}
              {detail.scoreBreakdown.feedback && (
                <div className="text-xs text-slate-500 space-y-0.5 pl-[140px]">
                  {detail.scoreBreakdown.feedback.topicsMatched?.length > 0 && (
                    <p>Topics matched: {detail.scoreBreakdown.feedback.topicsMatched.join(', ')}</p>
                  )}
                  {detail.scoreBreakdown.feedback.sourcesMatched?.length > 0 && (
                    <p>Sources matched: {detail.scoreBreakdown.feedback.sourcesMatched.join(', ')}</p>
                  )}
                  {detail.scoreBreakdown.feedback.eventCount != null && (
                    <p>Events: {detail.scoreBreakdown.feedback.eventCount}</p>
                  )}
                </div>
              )}
              <div className="pt-2 mt-2 border-t border-slate-200">
                <ScoreRow label="Final" score={detail.finalScore * 100} bold />
              </div>
            </div>
          </section>

          {/* Body / Snippet */}
          <section className="space-y-2">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Content</h3>
            <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">
              {detail.body || detail.snippet}
            </p>
          </section>

          {/* Inclusion / Exclusion Reason */}
          {detail.inclusionReason && (
            <section className="space-y-2">
              <h3 className="text-xs font-bold text-emerald-600 uppercase tracking-wider">Inclusion Reason</h3>
              <p className="text-sm text-slate-700 bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                {detail.inclusionReason}
              </p>
            </section>
          )}
          {detail.exclusionReason && (
            <section className="space-y-2">
              <h3 className="text-xs font-bold text-red-600 uppercase tracking-wider">Exclusion Reason</h3>
              <p className="text-sm text-slate-700 bg-red-50 border border-red-200 rounded-lg p-3">
                {detail.exclusionReason}
              </p>
            </section>
          )}

          {/* Cluster Relations */}
          {detail.clusterItems && detail.clusterItems.length > 0 && (
            <section className="space-y-2">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                Cluster Relations ({detail.clusterItems.length})
              </h3>
              <div className="divide-y divide-slate-100 border border-slate-200 rounded-lg overflow-hidden">
                {detail.clusterItems.map(ci => (
                  <div key={ci.id} className="px-3 py-2.5 hover:bg-slate-50 transition-colors">
                    <p className="text-xs font-medium text-slate-800 line-clamp-1">{ci.title}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[10px] text-slate-500">{ci.source}</span>
                      <ScoreBar score={ci.finalScore * 100} size="sm" showBar={false} />
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Linked Reports */}
          {detail.linkedReportIds && detail.linkedReportIds.length > 0 && (
            <section className="space-y-2">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Linked Reports</h3>
              <div className="flex flex-wrap gap-2">
                {detail.linkedReportIds.map(id => (
                  <span
                    key={id}
                    className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 bg-indigo-50 border border-indigo-200 rounded-md px-2.5 py-1"
                  >
                    <FileText className="w-3 h-3" />
                    {id}
                  </span>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
