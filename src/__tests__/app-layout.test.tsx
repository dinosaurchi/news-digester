// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { AppLayout } from '@/components/app-layout';
import { useAppStore } from '@/lib/store';
import { auth } from '@/lib/api';

vi.mock('@/components/sidebar', () => ({
  Sidebar: () => <div>Sidebar</div>,
}));

vi.mock('@/components/header', () => ({
  Header: () => <div>Header</div>,
}));

vi.mock('motion/react', () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  motion: {
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
      <div {...props}>{children}</div>
    ),
  },
}));

vi.mock('@/lib/api', () => ({
  auth: {
    me: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
  },
}));

function renderProtectedRoute(initialPath = '/workspaces') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login" element={<div>Login Page</div>} />
        <Route path="/" element={<AppLayout />}>
          <Route path="workspaces" element={<div>Protected Content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('AppLayout auth hydration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAppStore.setState({
      user: null,
      isLoggedIn: false,
      authStatus: 'unknown',
      currentWorkspace: null,
      isSidebarOpen: true,
    });
  });

  afterEach(() => {
    cleanup();
  });

  it('shows a loading state while auth status is unknown', () => {
    vi.mocked(auth.me).mockReturnValue(new Promise(() => {}));

    const { container } = renderProtectedRoute();

    expect(container.querySelector('.animate-spin')).toBeTruthy();
    expect(screen.queryByText('Protected Content')).toBeNull();
    expect(screen.queryByText('Login Page')).toBeNull();
  });

  it('renders protected content after auth.me succeeds', async () => {
    vi.mocked(auth.me).mockResolvedValue({
      id: 'user-1',
      username: 'tester',
      displayName: 'Tester',
      role: 'admin',
    });

    renderProtectedRoute();

    await waitFor(() => {
      expect(screen.getByText('Protected Content')).toBeTruthy();
    });

    const state = useAppStore.getState();
    expect(state.authStatus).toBe('authenticated');
    expect(state.isLoggedIn).toBe(true);
    expect(state.user?.displayName).toBe('Tester');
  });

  it('redirects to login after auth.me fails', async () => {
    vi.mocked(auth.me).mockRejectedValue(new Error('Unauthorized'));

    renderProtectedRoute();

    await waitFor(() => {
      expect(screen.getByText('Login Page')).toBeTruthy();
    });

    const state = useAppStore.getState();
    expect(state.authStatus).toBe('anonymous');
    expect(state.isLoggedIn).toBe(false);
    expect(state.user).toBeNull();
  });
});
