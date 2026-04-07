import { CheckCircle2, XCircle, Loader2, Circle, Minus } from 'lucide-react';
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
