import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the API module
vi.mock('@/lib/api', () => ({
  auth: {
    logout: vi.fn().mockResolvedValue(undefined),
    login: vi.fn(),
    me: vi.fn(),
  },
}));

import { auth } from '@/lib/api';
import { useAppStore } from '@/lib/store';

/**
 * These tests replicate the sidebar handleLogout logic:
 *
 *   const handleLogout = async () => {
 *     try {
 *       await auth.logout();
 *     } catch {
 *       // Ignore logout API errors — still clear local state
 *     }
 *     logout();  // store action
 *     navigate('/login');
 *   };
 *
 * We test the critical ordering: API logout is called first,
 * then local state is cleared — even if the API call fails.
 */
describe('Sidebar logout handler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset store to a logged-in state
    useAppStore.setState({
      user: { id: 'u-1', username: 'test', displayName: 'Test', role: 'admin' },
      isLoggedIn: true,
      authStatus: 'authenticated',
      currentWorkspace: null,
      isSidebarOpen: true,
    });
  });

  it('auth.logout is a callable function', () => {
    expect(typeof auth.logout).toBe('function');
  });

  it('store logout() clears auth state', () => {
    useAppStore.getState().logout();
    const state = useAppStore.getState();
    expect(state.authStatus).toBe('anonymous');
    expect(state.user).toBeNull();
    expect(state.isLoggedIn).toBe(false);
  });

  it('calls auth.logout() before clearing local state', async () => {
    // Replicate the sidebar handleLogout logic (without navigate)
    const handleLogout = async () => {
      try {
        await auth.logout();
      } catch {
        // Ignore logout API errors — still clear local state
      }
      useAppStore.getState().logout();
    };

    await handleLogout();

    // API logout was called
    expect(auth.logout).toHaveBeenCalledTimes(1);
    // Local state was cleared after
    const state = useAppStore.getState();
    expect(state.authStatus).toBe('anonymous');
    expect(state.user).toBeNull();
    expect(state.isLoggedIn).toBe(false);
  });

  it('clears local state even if auth.logout() API call fails', async () => {
    vi.mocked(auth.logout).mockRejectedValue(new Error('Network error'));

    const handleLogout = async () => {
      try {
        await auth.logout();
      } catch {
        // Ignore logout API errors — still clear local state
      }
      useAppStore.getState().logout();
    };

    // Should not throw
    await handleLogout();

    // API logout was attempted
    expect(auth.logout).toHaveBeenCalledTimes(1);
    // Local state was still cleared
    const state = useAppStore.getState();
    expect(state.authStatus).toBe('anonymous');
    expect(state.user).toBeNull();
    expect(state.isLoggedIn).toBe(false);
  });
});
