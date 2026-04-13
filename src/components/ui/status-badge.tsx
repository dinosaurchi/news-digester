import { cn } from '@/lib/utils';

type StatusVariant =
  | 'active'
  | 'paused'
  | 'archived'
  | 'healthy'
  | 'error'
  | 'disabled'
  | 'success'
  | 'failed'
  | 'running'
  | 'queued'
  | 'draft'
  | 'published'
  | 'included'
  | 'excluded'
  | 'pending';

const variantStyles: Record<StatusVariant, string> = {
  active: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  healthy: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  included: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  published: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  paused: 'bg-amber-50 text-amber-700 border-amber-200',
  pending: 'bg-amber-50 text-amber-700 border-amber-200',
  running: 'bg-blue-50 text-blue-700 border-blue-200',
  queued: 'bg-amber-50 text-amber-700 border-amber-200',
  draft: 'bg-slate-50 text-slate-600 border-slate-200',
  archived: 'bg-slate-50 text-slate-500 border-slate-200',
  disabled: 'bg-slate-50 text-slate-500 border-slate-200',
  error: 'bg-red-50 text-red-700 border-red-200',
  failed: 'bg-red-50 text-red-700 border-red-200',
  excluded: 'bg-red-50 text-red-600 border-red-200',
};

const dotStyles: Record<StatusVariant, string> = {
  active: 'bg-emerald-500',
  healthy: 'bg-emerald-500',
  success: 'bg-emerald-500',
  included: 'bg-emerald-500',
  published: 'bg-emerald-500',
  paused: 'bg-amber-500',
  pending: 'bg-amber-500',
  running: 'bg-blue-500',
  queued: 'bg-amber-500',
  draft: 'bg-slate-400',
  archived: 'bg-slate-400',
  disabled: 'bg-slate-400',
  error: 'bg-red-500',
  failed: 'bg-red-500',
  excluded: 'bg-red-400',
};

interface StatusBadgeProps {
  status: StatusVariant | string;
  label?: string;
  size?: 'sm' | 'md';
  className?: string;
}

export function StatusBadge({ status, label, size = 'sm', className }: StatusBadgeProps) {
  const variant = status.toLowerCase() as StatusVariant;
  const styles = variantStyles[variant] || variantStyles.draft;
  const dot = dotStyles[variant] || dotStyles.draft;
  const displayLabel = label || status.charAt(0).toUpperCase() + status.slice(1);

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 font-medium border rounded-full',
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm',
        styles,
        className
      )}
    >
      <span className={cn('w-1.5 h-1.5 rounded-full', dot)} />
      {displayLabel}
    </span>
  );
}
