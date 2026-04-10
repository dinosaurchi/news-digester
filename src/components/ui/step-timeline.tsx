import { CheckCircle2, XCircle, Loader2, Circle, Minus, AlertTriangle, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { RunStep } from '@/lib/types';

interface StepTimelineProps {
  steps: RunStep[];
}

const config = {
  pending:  { Icon: Circle,       color: 'text-slate-300', bg: 'bg-slate-100', ring: '',            line: 'bg-slate-200' },
  running:  { Icon: Loader2,      color: 'text-blue-500',  bg: 'bg-blue-50',   ring: 'ring-2 ring-blue-200', line: 'bg-blue-200' },
  success:  { Icon: CheckCircle2, color: 'text-emerald-500', bg: 'bg-emerald-50', ring: '',          line: 'bg-emerald-200' },
  failed:   { Icon: XCircle,      color: 'text-red-500',   bg: 'bg-red-50',    ring: 'ring-2 ring-red-200',   line: 'bg-red-200' },
  skipped:  { Icon: Minus,        color: 'text-slate-400', bg: 'bg-slate-50',  ring: '',            line: 'bg-slate-200' },
} as const;

function fmtDur(ms?: number): string {
  if (!ms) return '—';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const m = Math.floor(ms / 60000);
  const s = Math.round((ms % 60000) / 1000);
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

export function StepTimeline({ steps }: StepTimelineProps) {
  return (
    <div className="relative">
      {steps.map((step, idx) => {
        const c = config[step.status];
        const { Icon } = c;
        const isLast = idx === steps.length - 1;

        return (
          <div key={step.id} className="relative flex gap-3">
            {/* connector line */}
            {!isLast && (
              <div
                className={cn('absolute left-[13px] top-[30px] bottom-0 w-0.5', c.line)}
              />
            )}

            {/* icon circle */}
            <div
              className={cn(
                'w-[26px] h-[26px] rounded-full flex items-center justify-center shrink-0 z-10',
                c.bg,
                c.ring,
              )}
            >
              <Icon
                className={cn(
                  'w-3.5 h-3.5',
                  c.color,
                  step.status === 'running' && 'animate-spin',
                )}
              />
            </div>

            {/* content */}
            <div className="flex-1 pb-5 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <p
                  className={cn(
                    'text-sm font-medium truncate',
                    step.status === 'pending' ? 'text-slate-400' : 'text-slate-900',
                  )}
                >
                  {step.name}
                </p>
                <span className="text-xs text-slate-400 tabular-nums shrink-0">
                  {fmtDur(step.durationMs)}
                </span>
              </div>

              {/* Partial failure badge */}
              {step.metadata && (step.metadata.feedsFailed ?? 0) > 0 && step.status === 'success' && (
                <div className="mt-1">
                  <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-700 bg-amber-50 border border-amber-200 rounded-full px-2 py-0.5">
                    <AlertTriangle className="w-2.5 h-2.5" />
                    Partial: {step.metadata.feedsFailed} feed{(step.metadata.feedsFailed ?? 0) !== 1 ? 's' : ''} failed
                  </span>
                </div>
              )}

              {/* Metadata stats */}
              {step.metadata && (
                <div className="mt-1.5 text-[11px] text-slate-500 space-y-0.5">
                  {/* Feed stats */}
                  {(step.metadata.feedsSucceeded !== undefined || step.metadata.feedsFailed !== undefined) && (
                    <div>
                      <span className="text-slate-400">Feeds:</span>{' '}
                      <span className="font-medium text-emerald-600">{step.metadata.feedsSucceeded ?? 0} OK</span>
                      {step.metadata.feedsFailed != null && step.metadata.feedsFailed > 0 && (
                        <>
                          {' / '}
                          <span className="font-medium text-red-500">{step.metadata.feedsFailed} failed</span>
                        </>
                      )}
                    </div>
                  )}
                  {/* Entry stats */}
                  {(step.metadata.entriesFetched !== undefined || step.metadata.entriesImported !== undefined) && (
                    <div>
                      <span className="text-slate-400">Entries:</span>{' '}
                      {step.metadata.entriesFetched != null && <>{step.metadata.entriesFetched} fetched</>}
                      {step.metadata.entriesImported != null && (
                        <> → {step.metadata.entriesImported} imported</>
                      )}
                      {step.metadata.entriesSkipped != null && step.metadata.entriesSkipped > 0 && (
                        <>, {step.metadata.entriesSkipped} skipped</>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Feed details breakdown */}
              {step.metadata?.feedDetails && step.metadata.feedDetails.length > 0 && (
                <details className="mt-1.5 group/details">
                  <summary className="text-[11px] text-slate-400 cursor-pointer hover:text-slate-600 select-none inline-flex items-center gap-1">
                    <ChevronRight className="w-2.5 h-2.5 transition-transform group-open/details:rotate-90" />
                    {step.metadata.feedDetails.length} feed{step.metadata.feedDetails.length !== 1 ? 's' : ''} detail
                  </summary>
                  <div className="mt-1.5 space-y-1 ml-1 pl-3 border-l-2 border-slate-200">
                    {step.metadata.feedDetails.map(feed => (
                      <div key={feed.feedId} className="flex items-center gap-1.5 text-[11px]">
                        {feed.error ? (
                          <XCircle className="w-3 h-3 text-red-400 shrink-0" />
                        ) : (
                          <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
                        )}
                        <span className="font-medium text-slate-600 truncate max-w-[160px]">{feed.feedName}</span>
                        <span className="text-slate-400">{feed.entriesCount} entries</span>
                        {feed.error && (
                          <span className="text-red-400 truncate max-w-[200px]" title={feed.error}>{feed.error}</span>
                        )}
                      </div>
                    ))}
                  </div>
                </details>
              )}

              {step.error && (
                <div className="mt-1.5 text-xs text-red-700 bg-red-50 border border-red-200 rounded-md px-2.5 py-1.5">
                  {step.error}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
