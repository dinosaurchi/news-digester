'use client';

import { Search, Bell, Play, ChevronDown } from 'lucide-react';
import { useAppStore } from '@/lib/store';
import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import Link from 'next/link';

export function Header() {
  const { isSidebarOpen, currentWorkspace } = useAppStore();
  const params = useParams();
  const workspaceId = params.workspaceId as string;

  return (
    <header 
      className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 sticky top-0 z-40"
    >
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-semibold text-slate-900">
          {currentWorkspace ? currentWorkspace.name : 'Workspaces'}
        </h1>
        {workspaceId && (
          <div className="h-4 w-px bg-slate-300 mx-2" />
        )}
        <div className="relative hidden md:block">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search..." 
            className="pl-10 pr-4 py-1.5 bg-slate-50 border border-slate-200 rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 w-64"
          />
        </div>
      </div>

      <div className="flex items-center gap-4">
        {workspaceId && (
          <button className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors shadow-sm">
            <Play className="w-4 h-4 fill-current" />
            Run Now
          </button>
        )}
        
        <button className="p-2 text-slate-500 hover:bg-slate-100 rounded-full transition-colors relative">
          <Bell className="w-5 h-5" />
          <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full border-2 border-white" />
        </button>

        <div className="h-8 w-px bg-slate-200" />

        <Link href="/profile" className="flex items-center gap-2 hover:bg-slate-50 p-1 rounded-lg transition-colors">
          <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center text-xs font-bold">
            {useAppStore.getState().user?.displayName?.charAt(0) || 'U'}
          </div>
          <ChevronDown className="w-4 h-4 text-slate-400" />
        </Link>
      </div>
    </header>
  );
}
