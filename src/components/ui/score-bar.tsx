import { cn } from '@/lib/utils';

interface ScoreBarProps {
  score: number; // 0-100
  label?: string;
  showBar?: boolean;
  size?: 'sm' | 'md';
  bold?: boolean;
}

export function ScoreBar({ score, label, showBar = true, size = 'sm', bold = false }: ScoreBarProps) {
  const clamped = Math.max(0, Math.min(100, score));
  const color =
    clamped > 80 ? 'text-emerald-600' : clamped > 50 ? 'text-amber-600' : 'text-red-600';
  const barColor =
    clamped > 80 ? 'bg-emerald-500' : clamped > 50 ? 'bg-amber-500' : 'bg-red-500';

  return (
    <div className="flex items-center gap-2">
      <span
        className={cn(
          'tabular-nums',
          size === 'sm' ? 'text-xs' : 'text-sm',
          bold && 'font-bold',
          color,
        )}
      >
        {Math.round(clamped)}
      </span>
      {showBar && (
        <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden min-w-[32px]">
          <div
            className={cn('h-full rounded-full transition-all duration-300', barColor)}
            style={{ width: `${clamped}%` }}
          />
        </div>
      )}
      {label && (
        <span className="text-[10px] font-medium text-slate-400 uppercase leading-none">
          {label}
        </span>
      )}
    </div>
  );
}
