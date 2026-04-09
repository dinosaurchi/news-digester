import { create } from 'zustand';
import { Workspace } from './types';

export type AuthStatus = 'unknown' | 'authenticated' | 'anonymous';

export interface User {
  id: string;
  username: string;
  displayName: string;
  role: string;
}

interface AppState {
  user: User | null;
  setUser: (user: User | null) => void;
  isLoggedIn: boolean;
  setLoggedIn: (loggedIn: boolean) => void;
  authStatus: AuthStatus;
  setAuthStatus: (status: AuthStatus) => void;
  currentWorkspace: Workspace | null;
  setCurrentWorkspace: (workspace: Workspace | null) => void;
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  logout: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  user: null,
  setUser: (user) => set({ user }),
  isLoggedIn: false,
  setLoggedIn: (loggedIn) => set({
    isLoggedIn: loggedIn,
    authStatus: loggedIn ? 'authenticated' : 'anonymous',
  }),
  authStatus: 'unknown',
  setAuthStatus: (status) => set({ authStatus: status }),
  currentWorkspace: null,
  setCurrentWorkspace: (workspace) => set({ currentWorkspace: workspace }),
  isSidebarOpen: true,
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  setSidebarOpen: (open) => set({ isSidebarOpen: open }),
  logout: () => set({
    user: null,
    isLoggedIn: false,
    authStatus: 'anonymous',
    currentWorkspace: null,
  }),
}));
