import { cn } from '@/lib/utils';

interface TypingIndicatorProps {
  className?: string;
  label?: string;
}

export function TypingIndicator({ className, label = 'Agent is typing' }: TypingIndicatorProps) {
  return (
    <div className={cn('flex items-center gap-3', className)}>
      <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center shrink-0">
        <div className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
          <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
          <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce" />
        </div>
      </div>
      <span className="text-xs text-slate-400 italic">{label}</span>
    </div>
  );
}
