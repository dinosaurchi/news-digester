import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Bell, Play, LogOut, ChevronDown, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { useAppStore } from '@/lib/store';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { api, auth } from '@/lib/api';
import { cn } from '@/lib/utils';
import { WorkspaceSwitcher } from './workspace-switcher';

export function Header() {
  const { currentWorkspace, setCurrentWorkspace, logout, user } = useAppStore();
  const params = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const workspaceId = params.workspaceId as string | undefined;

  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Fetch workspace when entering a workspace route
  const { data: workspace } = useQuery({
    queryKey: ['workspace', workspaceId],
    queryFn: () => api.workspaces.get(workspaceId!),
    enabled: !!workspaceId,
  });

  useEffect(() => {
    if (workspace) {
      setCurrentWorkspace(workspace);
    } else if (!workspaceId) {
      setCurrentWorkspace(null);
    }
  }, [workspace, workspaceId, setCurrentWorkspace]);

  // Run Now mutation
  const runMutation = useMutation({
    mutationFn: () => api.runs.trigger(workspaceId!),
    onSuccess: () => {
      setToast({ type: 'success', message: 'Intelligence cycle triggered successfully.' });
      queryClient.invalidateQueries({ queryKey: ['runs', workspaceId] });
    },
    onError: () => {
      setToast({ type: 'error', message: 'Failed to trigger run. Please try again.' });
    },
  });

  const handleLogout = async () => {
    setUserMenuOpen(false);
    try {
      await auth.logout();
    } catch {
      // Ignore logout API errors — still clear local state
    }
    logout();
    navigate('/login');
  };

  // Build breadcrumb
  const breadcrumb = buildBreadcrumb(location.pathname, currentWorkspace);

  // Auto-dismiss toast
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  return (
    <>
      <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-6 sticky top-0 z-40">
        {/* Left: Breadcrumb */}
        <div className="flex items-center gap-2 min-w-0">
          {breadcrumb.length > 0 ? (
            <nav className="flex items-center gap-1.5 text-sm min-w-0">
              {breadcrumb.map((crumb, i) => (
                <span key={i} className="flex items-center gap-1.5">
                  {i > 0 && (
                    <span className="text-slate-300 shrink-0">/</span>
                  )}
                  {crumb.to ? (
                    <a
                      href={crumb.to}
                      onClick={(e) => {
                        e.preventDefault();
                        navigate(crumb.to!);
                      }}
                      className="text-slate-500 hover:text-slate-700 transition-colors truncate"
                    >
                      {crumb.label}
                    </a>
                  ) : (
                    <span className="text-slate-900 font-medium truncate">{crumb.label}</span>
                  )}
                </span>
              ))}
            </nav>
          ) : (
            <h1 className="text-sm font-semibold text-slate-900">Workspaces</h1>
          )}
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2 shrink-0">
          {/* Workspace switcher (only inside workspace) */}
          {workspaceId && <WorkspaceSwitcher />}

          {/* Run Now button (only inside workspace) */}
          {workspaceId && (
            <button
              onClick={() => runMutation.mutate()}
              disabled={runMutation.isPending}
              className={cn(
                'flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all shadow-sm',
                runMutation.isPending
                  ? 'bg-indigo-400 text-white cursor-wait'
                  : 'bg-indigo-600 hover:bg-indigo-700 text-white'
              )}
            >
              {runMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-3.5 h-3.5 fill-current" />
              )}
              {runMutation.isPending ? 'Running...' : 'Run Now'}
            </button>
          )}

          {/* Notification bell (decorative) */}
          <button className="p-2 text-slate-500 hover:bg-slate-100 rounded-lg transition-colors relative" title="Notifications">
            <Bell className="w-[18px] h-[18px]" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full ring-2 ring-white" />
          </button>

          <div className="h-6 w-px bg-slate-200 mx-1" />

          {/* User menu */}
          <div className="relative">
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="flex items-center gap-2 hover:bg-slate-50 p-1.5 rounded-lg transition-colors"
            >
              <div className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center text-xs font-bold">
                {user?.displayName?.charAt(0) || 'U'}
              </div>
              <span className="text-sm text-slate-700 font-medium hidden md:inline">
                {user?.displayName}
              </span>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            </button>

            {userMenuOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setUserMenuOpen(false)} />
                <div className="absolute right-0 top-full mt-1 w-52 bg-white border border-slate-200 rounded-xl shadow-lg z-50 overflow-hidden">
                  <div className="px-3 py-2.5 border-b border-slate-100">
                    <p className="text-sm font-medium text-slate-900">{user?.displayName}</p>
                    <p className="text-xs text-slate-500 capitalize">{user?.role}</p>
                  </div>
                  <div className="p-1">
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <LogOut className="w-4 h-4" />
                      Sign out
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Toast notification */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-[100] animate-in fade-in slide-in-from-bottom-2">
          <div
            className={cn(
              'flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg border text-sm font-medium',
              toast.type === 'success'
                ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                : 'bg-red-50 border-red-200 text-red-800'
            )}
          >
            {toast.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            ) : (
              <AlertCircle className="w-4 h-4 text-red-600" />
            )}
            {toast.message}
          </div>
        </div>
      )}
    </>
  );
}

/* ---- Helpers ---- */

interface BreadcrumbItem {
  label: string;
  to?: string;
}

function buildBreadcrumb(pathname: string, workspace: ReturnType<typeof useAppStore.getState>['currentWorkspace']): BreadcrumbItem[] {
  const crumbs: BreadcrumbItem[] = [];

  // Always start with Workspaces
  crumbs.push({ label: 'Workspaces', to: '/workspaces' });

  // Parse workspace segment
  const wsMatch = pathname.match(/\/workspaces\/([^/]+)/);
  if (wsMatch && workspace) {
    crumbs.push({
      label: workspace.name,
      to: `/workspaces/${wsMatch[1]}`,
    });

    // Parse sub-page segment
    const segments = pathname.split('/').filter(Boolean);
    if (segments.length > 2) {
      const subPage = segments[2];
      const subLabels: Record<string, string> = {
        profile: 'Profile',
        feeds: 'Feeds',
        content: 'Content',
        reports: 'Reports',
        runs: 'Runs',
        feedback: 'Feedback',
        settings: 'Settings',
      };
      if (subLabels[subPage]) {
        crumbs.push({ label: subLabels[subPage] });
      }
      // If there's a threadId, don't add it as a crumb (it's a detail page)
    }
  }

  return crumbs;
}
