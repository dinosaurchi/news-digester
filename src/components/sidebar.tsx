import { Link, useNavigate, useParams, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Briefcase,
  Rss,
  FileText,
  PlayCircle,
  ThumbsUp,
  Settings,
  ChevronLeft,
  ChevronRight,
  Building2,
  LogOut,
  FileBarChart,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAppStore } from '@/lib/store';

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

export function Sidebar() {
  const location = useLocation();
  const params = useParams();
  const navigate = useNavigate();
  const workspaceId = params.workspaceId as string | undefined;
  const { isSidebarOpen, toggleSidebar, user, logout } = useAppStore();

  // Determine if we're inside a workspace route
  const isInWorkspace = !!workspaceId;

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const workspaceNavItems: NavItem[] = workspaceId
    ? [
        { name: 'Overview', href: `/workspaces/${workspaceId}`, icon: LayoutDashboard },
        { name: 'Profile', href: `/workspaces/${workspaceId}/profile`, icon: Building2 },
        { name: 'Feeds', href: `/workspaces/${workspaceId}/feeds`, icon: Rss },
        { name: 'Content', href: `/workspaces/${workspaceId}/content`, icon: FileText },
        { name: 'Reports', href: `/workspaces/${workspaceId}/reports`, icon: FileBarChart },
        { name: 'Runs', href: `/workspaces/${workspaceId}/runs`, icon: PlayCircle },
        { name: 'Feedback', href: `/workspaces/${workspaceId}/feedback`, icon: ThumbsUp },
        { name: 'Settings', href: `/workspaces/${workspaceId}/settings`, icon: Settings },
      ]
    : [];

  const isActive = (item: NavItem) => {
    if (item.name === 'Overview') {
      return location.pathname === item.href;
    }
    if (item.name === 'Reports') {
      return location.pathname === item.href || location.pathname.startsWith(`/workspaces/${workspaceId}/reports/`);
    }
    return location.pathname.startsWith(item.href);
  };

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 h-screen bg-slate-900 text-slate-300 transition-all duration-300 ease-in-out z-50 flex flex-col border-r border-slate-800',
        isSidebarOpen ? 'w-64' : 'w-[68px]'
      )}
    >
      {/* Brand / Logo */}
      <div className="h-14 flex items-center justify-between px-4 border-b border-slate-800 shrink-0">
        <Link to="/workspaces" className="flex items-center gap-2.5 overflow-hidden">
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center shrink-0">
            <Briefcase className="w-4.5 h-4.5 text-white" />
          </div>
          {isSidebarOpen && (
            <span className="font-bold text-white text-[15px] whitespace-nowrap">SME Admin</span>
          )}
        </Link>
        {isSidebarOpen && (
          <button
            onClick={toggleSidebar}
            className="p-1.5 hover:bg-slate-800 rounded-md transition-colors text-slate-500 hover:text-slate-300"
            title="Collapse sidebar"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1 scrollbar-thin">
        {!isInWorkspace ? (
          // Global nav (outside workspace)
          <SidebarLink
            to="/workspaces"
            icon={Briefcase}
            label="Workspaces"
            isCollapsed={!isSidebarOpen}
            active={location.pathname === '/workspaces'}
          />
        ) : (
          // Workspace nav
          <>
            <SidebarLink
              to="/workspaces"
              icon={ChevronLeft}
              label="Back to Workspaces"
              isCollapsed={!isSidebarOpen}
              active={false}
              muted
            />

            {isSidebarOpen && (
              <div className="mt-5 mb-2 px-3">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                  {useAppStore.getState().currentWorkspace?.name || 'Workspace'}
                </p>
              </div>
            )}

            {!isSidebarOpen && <div className="my-3 mx-2 border-t border-slate-800" />}

            {workspaceNavItems.map((item) => (
              <SidebarLink
                key={item.name}
                to={item.href}
                icon={item.icon}
                label={item.name}
                isCollapsed={!isSidebarOpen}
                active={isActive(item)}
              />
            ))}
          </>
        )}
      </nav>

      {/* Collapse toggle (when collapsed) / User section */}
      <div className="border-t border-slate-800 p-3 shrink-0">
        {!isSidebarOpen && (
          <button
            onClick={toggleSidebar}
            className="w-full flex items-center justify-center p-2 hover:bg-slate-800 rounded-lg transition-colors text-slate-500 hover:text-slate-300 mb-2"
            title="Expand sidebar"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        )}
        <div className="flex items-center gap-2.5 px-2 py-1.5">
          <div className="w-8 h-8 rounded-full bg-indigo-600/20 flex items-center justify-center text-xs font-bold text-indigo-400 shrink-0">
            {user?.displayName?.charAt(0) || 'U'}
          </div>
          {isSidebarOpen && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-200 truncate">{user?.displayName}</p>
              <p className="text-xs text-slate-500 truncate capitalize">{user?.role}</p>
            </div>
          )}
          {isSidebarOpen && (
            <button
              onClick={handleLogout}
              className="p-1.5 hover:bg-slate-800 rounded-md text-slate-500 hover:text-red-400 transition-colors shrink-0"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}

/* ---- Internal sub-components ---- */

interface SidebarLinkProps {
  to: string;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  isCollapsed: boolean;
  active: boolean;
  muted?: boolean;
}

function SidebarLink({ to, icon: Icon, label, isCollapsed, active, muted }: SidebarLinkProps) {
  return (
    <Link
      to={to}
      className={cn(
        'group relative flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-150',
        active
          ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-500/20'
          : muted
            ? 'text-slate-500 hover:bg-slate-800 hover:text-slate-300'
            : 'text-slate-400 hover:bg-slate-800 hover:text-white'
      )}
      title={isCollapsed ? label : undefined}
    >
      {/* Active indicator bar */}
      {active && !isCollapsed && (
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-white rounded-r-full" />
      )}
      <Icon className="w-5 h-5 shrink-0" />
      {!isCollapsed && <span className="text-sm font-medium whitespace-nowrap">{label}</span>}
      {/* Tooltip when collapsed */}
      {isCollapsed && (
        <div className="absolute left-full ml-2 px-2.5 py-1 bg-slate-800 text-white text-xs rounded-md opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all whitespace-nowrap z-[60] shadow-lg pointer-events-none">
          {label}
        </div>
      )}
    </Link>
  );
}
