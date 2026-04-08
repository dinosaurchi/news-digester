import { describe, it, expect, beforeEach } from 'vitest';
import { useAppStore } from '@/lib/store';

describe('Store authStatus', () => {
  beforeEach(() => {
    // Reset store to initial state before each test
    useAppStore.setState({
      user: null,
      isLoggedIn: false,
      authStatus: 'unknown',
      currentWorkspace: null,
      isSidebarOpen: true,
    });
  });

  it('initializes with authStatus === "unknown"', () => {
    const state = useAppStore.getState();
    expect(state.authStatus).toBe('unknown');
  });

  it('setAuthStatus("authenticated") updates the status', () => {
    useAppStore.getState().setAuthStatus('authenticated');
    expect(useAppStore.getState().authStatus).toBe('authenticated');
  });

  it('setAuthStatus("anonymous") updates the status', () => {
    useAppStore.getState().setAuthStatus('anonymous');
    expect(useAppStore.getState().authStatus).toBe('anonymous');
  });

  it('setLoggedIn(true) also sets authStatus to "authenticated"', () => {
    useAppStore.getState().setLoggedIn(true);
    const state = useAppStore.getState();
    expect(state.isLoggedIn).toBe(true);
    expect(state.authStatus).toBe('authenticated');
  });

  it('setLoggedIn(false) also sets authStatus to "anonymous"', () => {
    // First log in
    useAppStore.getState().setLoggedIn(true);
    // Then log out via setLoggedIn
    useAppStore.getState().setLoggedIn(false);
    const state = useAppStore.getState();
    expect(state.isLoggedIn).toBe(false);
    expect(state.authStatus).toBe('anonymous');
  });

  it('logout() sets authStatus to "anonymous" and clears user', () => {
    // Set up a logged-in state
    useAppStore.setState({
      user: { id: 'u-1', username: 'test', displayName: 'Test', role: 'admin' },
      isLoggedIn: true,
      authStatus: 'authenticated',
      currentWorkspace: { id: 'w-1', name: 'Test WS', customer: 'Test', status: 'active', createdAt: '', updatedAt: '', feedCount: 0 },
    });

    useAppStore.getState().logout();

    const state = useAppStore.getState();
    expect(state.authStatus).toBe('anonymous');
    expect(state.user).toBeNull();
    expect(state.isLoggedIn).toBe(false);
    expect(state.currentWorkspace).toBeNull();
  });
});
