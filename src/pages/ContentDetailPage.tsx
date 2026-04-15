import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ChevronLeft, FileText, Tag, Calendar, Link2, Hash,
  CheckCircle, XCircle, Info, Sparkles, AlertTriangle, Globe,
} from 'lucide-react';
import { formatDateOnly, cn } from '@/lib/utils';
import { PageHeader } from '@/components/ui/page-header';
import { StatusBadge } from '@/components/ui/status-badge';
import { Skeleton } from '@/components/ui/loading-skeleton';
import { ScoreBar } from '@/components/ui/score-bar';
import type { ContentType, ThemeMatch, CompetitorMatch, MultiSignalBoost } from '@/lib/types';

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const GOOGLE_NEWS_URL_RE = /^https?:\/\/news\.google\.com\//i;

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

function ScoreRow({ label, score, bold, tooltip }: { label: string; score: number; bold?: boolean; tooltip?: string }) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-1.5 min-w-[140px]">
        <span className="text-xs font-medium text-slate-500">{label}</span>
        {tooltip && (
          <span className="group relative">
            <Info className="w-3 h-3 text-slate-400 cursor-help" />
            <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-[10px] text-white bg-slate-800 rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap max-w-[200px] text-center z-10">
              {tooltip}
            </span>
          </span>
        )}
      </div>
      <div className="flex-1">
        <ScoreBar score={score} bold={bold} />
      </div>
    </div>
  );
}

function ThemeMatchSection({ themeMatch }: { themeMatch: ThemeMatch }) {
  if (!themeMatch) return null;
  return (
    <div className="pt-2 mt-2 border-t border-slate-200">
      <h4 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">Theme Match Details</h4>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="flex items-center gap-1 mb-1">
            <CheckCircle className="w-3 h-3 text-emerald-500" />
            <span className="text-[10px] font-medium text-slate-500">Matched ({themeMatch.matched.length})</span>
          </div>
          {themeMatch.matched.length > 0 ? (
            <div className="flex flex-wrap gap-1">
              {themeMatch.matched.map((theme, i) => (
                <span key={i} className="inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 rounded">
                  {theme}
                </span>
              ))}
            </div>
          ) : (
            <span className="text-[10px] text-slate-400 italic">No themes matched</span>
          )}
        </div>
        <div>
          <div className="flex items-center gap-1 mb-1">
            <XCircle className="w-3 h-3 text-slate-400" />
            <span className="text-[10px] font-medium text-slate-500">Unmatched ({themeMatch.unmatched.length})</span>
          </div>
          {themeMatch.unmatched.length > 0 ? (
            <div className="flex flex-wrap gap-1">
              {themeMatch.unmatched.map((theme, i) => (
                <span key={i} className="inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium bg-slate-50 text-slate-500 border border-slate-200 rounded">
                  {theme}
                </span>
              ))}
            </div>
          ) : (
            <span className="text-[10px] text-slate-400 italic">All themes matched</span>
          )}
        </div>
      </div>
    </div>
  );
}

function CompetitorMatchSection({ competitorMatch }: { competitorMatch: CompetitorMatch }) {
  if (!competitorMatch) return null;
  return (
    <div className="pt-2 mt-2 border-t border-slate-200">
      <h4 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">Competitor Match Details</h4>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="flex items-center gap-1 mb-1">
            <CheckCircle className="w-3 h-3 text-emerald-500" />
            <span className="text-[10px] font-medium text-slate-500">Matched ({competitorMatch.matched.length})</span>
          </div>
          {competitorMatch.matched.length > 0 ? (
            <div className="flex flex-wrap gap-1">
              {competitorMatch.matched.map((comp, i) => (
                <span key={i} className="inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium bg-orange-50 text-orange-700 border border-orange-200 rounded">
                  {comp}
                </span>
              ))}
            </div>
          ) : (
            <span className="text-[10px] text-slate-400 italic">No competitors mentioned</span>
          )}
        </div>
        <div>
          <div className="flex items-center gap-1 mb-1">
            <XCircle className="w-3 h-3 text-slate-400" />
            <span className="text-[10px] font-medium text-slate-500">Not Found ({competitorMatch.unmatched.length})</span>
          </div>
          {competitorMatch.unmatched.length > 0 ? (
            <div className="flex flex-wrap gap-1">
              {competitorMatch.unmatched.map((comp, i) => (
                <span key={i} className="inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium bg-slate-50 text-slate-500 border border-slate-200 rounded">
                  {comp}
                </span>
              ))}
            </div>
          ) : (
            <span className="text-[10px] text-slate-400 italic">All competitors mentioned</span>
          )}
        </div>
      </div>
    </div>
  );
}

function MultiSignalBoostBadge({ boost }: { boost: MultiSignalBoost }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg">
      <Sparkles className="w-3.5 h-3.5 text-amber-600" />
      <div>
        <span className="text-[10px] font-semibold text-amber-700 uppercase tracking-wider">Multi-Signal Boost</span>
        <p className="text-[10px] text-amber-600">
          +{(boost.bonus * 100).toFixed(1)}% bonus for matching {boost.distinct_matched_themes} distinct theme{boost.distinct_matched_themes !== 1 ? 's' : ''}
        </p>
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
              {detail.publisherName && detail.publisherName !== detail.source && (
                <MetaRow icon={Globe} label="Publisher" value={detail.publisherName} />
              )}
              {detail.publisherDomain && (
                <MetaRow
                  icon={Globe}
                  label="Domain"
                  value={
                    <a
                      href={`https://${detail.publisherDomain}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-indigo-600 hover:underline"
                    >
                      {detail.publisherDomain}
                    </a>
                  }
                />
              )}
              <MetaRow icon={Calendar} label="Published" value={formatDateOnly(detail.publishedAt)} />
              <MetaRow
                icon={Link2}
                label="URL"
                value={
                  <div className="space-y-1">
                    <a href={detail.sourceUrl} target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:underline truncate block">
                      {detail.sourceUrl}
                    </a>
                    {GOOGLE_NEWS_URL_RE.test(detail.sourceUrl) && (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium bg-amber-50 text-amber-700 border border-amber-200 rounded">
                        <AlertTriangle className="w-3 h-3" />
                        Google News link — may expire
                      </span>
                    )}
                  </div>
                }
              />
              {detail.clusterId && (
                <MetaRow icon={Hash} label="Cluster" value={detail.clusterId} />
              )}
            </div>
          </section>

          {/* Score Breakdown — all scores are deterministic/lexical (keyword, BM25, freshness, source authority).
              No LLM or semantic model is used for content scoring. LLM is used only for
              shortlist reranking and report generation. */}
          <section className="space-y-2.5">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Score Breakdown</h3>
              <span className="text-[9px] font-medium text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">
                Deterministic scoring · No LLM
              </span>
            </div>
            <div className="bg-slate-50 rounded-lg p-4 space-y-3">
              <ScoreRow
                label="Relevance"
                score={detail.scoreBreakdown.relevance * 100}
                tooltip="Weighted combination of keyword matching against priority themes"
              />
              <ScoreRow
                label="BM25 (Lexical)"
                score={detail.scoreBreakdown.bm25 * 100}
                tooltip="Lexical relevance score based on term frequency matching. NOT an LLM/semantic score."
              />
              <ScoreRow
                label="Freshness"
                score={detail.scoreBreakdown.freshness * 100}
                tooltip="Time-decay score based on publish date. Recent content scores higher."
              />
              <ScoreRow
                label="Source Authority"
                score={detail.scoreBreakdown.sourceAuthority * 100}
                tooltip="Domain trust score. Trusted domains (e.g., reuters.com) score higher."
              />
              {detail.scoreBreakdown.feedbackAdjustment != null && (
                <ScoreRow
                  label="Feedback Adj."
                  score={detail.scoreBreakdown.feedbackAdjustment * 100}
                  tooltip="Score adjustment from user preference signals"
                />
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
              
              {/* Multi-signal boost indicator */}
              {detail.scoreBreakdown.multiSignalBoost && (
                <MultiSignalBoostBadge boost={detail.scoreBreakdown.multiSignalBoost} />
              )}
              
              {/* Theme match details */}
              {detail.scoreBreakdown.themeMatch && (
                <ThemeMatchSection themeMatch={detail.scoreBreakdown.themeMatch} />
              )}
              
              {/* Competitor match details */}
              {detail.scoreBreakdown.competitorMatch && (
                <CompetitorMatchSection competitorMatch={detail.scoreBreakdown.competitorMatch} />
              )}
              
              {/* Filter reason info */}
              {detail.scoreBreakdown.filterReason && (
                <div className="pt-2 mt-2 border-t border-slate-200">
                  <div className="flex items-center gap-2">
                    <Info className="w-3 h-3 text-slate-400" />
                    <span className="text-[10px] text-slate-500">
                      Filter: <span className={cn(
                        "font-medium",
                        detail.scoreBreakdown.filterReason === 'included' ? "text-emerald-600" : "text-red-600"
                      )}>{detail.scoreBreakdown.filterReason === 'included' ? 'Included' : detail.scoreBreakdown.filterReason.replace(/_/g, ' ')}</span>
                      {detail.scoreBreakdown.minRelevanceThreshold != null && (
                        <span className="text-slate-400">
                          {' '}(threshold: {(detail.scoreBreakdown.minRelevanceThreshold * 100).toFixed(0)}%)
                        </span>
                      )}
                    </span>
                  </div>
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
