import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { Check, ChevronsUpDown, Briefcase } from 'lucide-react';
import { cn } from '@/lib/utils';
import { StatusBadge } from './ui/status-badge';

export function WorkspaceSwitcher() {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { currentWorkspace } = useAppStore();

  const { data: workspaces } = useQuery({
    queryKey: ['workspaces'],
    queryFn: api.workspaces.list,
  });

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (workspaceId: string) => {
    setIsOpen(false);
    navigate(`/workspaces/${workspaceId}`);
  };

  return (
    <div className="relative" ref={containerRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-sm hover:bg-slate-100 transition-colors min-w-[180px]"
      >
        <Briefcase className="w-4 h-4 text-slate-500 shrink-0" />
        <span className="truncate text-slate-700 font-medium">
          {currentWorkspace?.name || 'Select workspace...'}
        </span>
        <ChevronsUpDown className="w-3.5 h-3.5 text-slate-400 shrink-0 ml-auto" />
      </button>

      {isOpen && workspaces && (
        <div className="absolute top-full left-0 mt-1 w-72 bg-white border border-slate-200 rounded-xl shadow-lg z-50 overflow-hidden">
          <div className="p-2 border-b border-slate-100">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-2 py-1">Workspaces</p>
          </div>
          <div className="max-h-64 overflow-y-auto p-1">
            {workspaces.map((ws) => (
              <button
                key={ws.id}
                onClick={() => handleSelect(ws.id)}
                className={cn(
                  'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors',
                  currentWorkspace?.id === ws.id
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'hover:bg-slate-50 text-slate-700'
                )}
              >
                <div className={cn(
                  'w-8 h-8 rounded-lg flex items-center justify-center shrink-0',
                  currentWorkspace?.id === ws.id
                    ? 'bg-indigo-100 text-indigo-600'
                    : 'bg-slate-100 text-slate-500'
                )}>
                  <Briefcase className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{ws.name}</p>
                  <p className="text-xs text-slate-500 truncate">{ws.customer}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <StatusBadge status={ws.status} />
                  {currentWorkspace?.id === ws.id && (
                    <Check className="w-4 h-4 text-indigo-600" />
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
