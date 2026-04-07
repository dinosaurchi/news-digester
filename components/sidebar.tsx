'use client';

import Link from 'next/link';
import { usePathname, useParams } from 'next/navigation';
import { 
  LayoutDashboard, 
  Briefcase, 
  Rss, 
  FileText, 
  MessageSquare, 
  PlayCircle, 
  ThumbsUp, 
  Settings,
  ChevronLeft,
  ChevronRight,
  Building2
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAppStore } from '@/lib/store';
import { useRouter } from 'next/navigation';
import { LogOut } from 'lucide-react';

export function Sidebar() {
  const pathname = usePathname();
  const params = useParams();
  const router = useRouter();
  const workspaceId = params.workspaceId as string;
  const { isSidebarOpen, toggleSidebar, user, setUser } = useAppStore();

  const handleLogout = async () => {
    await fetch('/api/auth/logout', { method: 'POST' });
    setUser(null);
    router.push('/login');
  };

  const navItems = [
    { name: 'Overview', href: `/workspaces/${workspaceId}`, icon: LayoutDashboard },
    { name: 'Profile', href: `/workspaces/${workspaceId}/profile`, icon: Building2 },
    { name: 'Feeds', href: `/workspaces/${workspaceId}/feeds`, icon: Rss },
    { name: 'Content', href: `/workspaces/${workspaceId}/content`, icon: FileText },
    { name: 'Reports', href: `/workspaces/${workspaceId}/reports`, icon: MessageSquare },
    { name: 'Runs', href: `/workspaces/${workspaceId}/runs`, icon: PlayCircle },
    { name: 'Feedback', href: `/workspaces/${workspaceId}/feedback`, icon: ThumbsUp },
    { name: 'Settings', href: `/workspaces/${workspaceId}/settings`, icon: Settings },
  ];

  return (
    <aside 
      className={cn(
        "fixed left-0 top-0 h-screen bg-slate-900 text-slate-300 transition-all duration-300 z-50 flex flex-col border-r border-slate-800",
        isSidebarOpen ? "w-64" : "w-20"
      )}
    >
      <div className="h-16 flex items-center justify-between px-6 border-b border-slate-800">
        <Link href="/workspaces" className="flex items-center gap-3 overflow-hidden">
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center shrink-0">
            <Briefcase className="w-5 h-5 text-white" />
          </div>
          {isSidebarOpen && <span className="font-bold text-white truncate">SME Admin</span>}
        </Link>
        <button 
          onClick={toggleSidebar}
          className="p-1.5 hover:bg-slate-800 rounded-md transition-colors"
        >
          {isSidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto py-6 px-3 space-y-1">
        {!workspaceId ? (
          <Link
            href="/workspaces"
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all group",
              pathname === '/workspaces' ? "bg-indigo-600 text-white" : "hover:bg-slate-800 hover:text-white"
            )}
          >
            <Briefcase className="w-5 h-5 shrink-0" />
            {isSidebarOpen && <span className="font-medium">All Workspaces</span>}
          </Link>
        ) : (
          <>
            <Link
              href="/workspaces"
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-slate-800 hover:text-white transition-all group mb-4 text-slate-400"
            >
              <ChevronLeft className="w-5 h-5 shrink-0" />
              {isSidebarOpen && <span className="font-medium">Back to List</span>}
            </Link>
            
            <div className="px-3 mb-2">
              {isSidebarOpen && <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Workspace Menu</p>}
            </div>

            {navItems.map((item) => {
              const isActive = pathname === item.href || (item.name === 'Reports' && pathname.startsWith(`/workspaces/${workspaceId}/reports/`));
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all group relative",
                    isActive ? "bg-indigo-600 text-white" : "hover:bg-slate-800 hover:text-white"
                  )}
                >
                  <item.icon className="w-5 h-5 shrink-0" />
                  {isSidebarOpen && <span className="font-medium">{item.name}</span>}
                  {!isSidebarOpen && isActive && (
                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-white rounded-r-full" />
                  )}
                </Link>
              );
            })}
          </>
        )}
      </div>

      <div className="p-4 border-t border-slate-800">
        <div className="flex items-center justify-between gap-3 px-2 py-2">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-xs font-bold text-white shrink-0">
              {user?.displayName?.charAt(0) || 'U'}
            </div>
            {isSidebarOpen && (
              <div className="overflow-hidden">
                <p className="text-sm font-medium text-white truncate">{user?.displayName}</p>
                <p className="text-xs text-slate-500 truncate capitalize">{user?.role}</p>
              </div>
            )}
          </div>
          {isSidebarOpen && (
            <button 
              onClick={handleLogout}
              className="p-1.5 hover:bg-slate-800 rounded-md text-slate-500 hover:text-red-400 transition-colors"
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
