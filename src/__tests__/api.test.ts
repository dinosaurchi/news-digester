import { describe, it, expect, vi } from 'vitest';

// Mock the API client module before importing auth
vi.mock('@/lib/api-client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from '@/lib/api-client';
import { auth } from '@/lib/api';

describe('API auth.me() unwrapping', () => {
  it('returns the unwrapped user object from the response', async () => {
    const mockUser = { id: 'u-1', username: 'test', displayName: 'Test', role: 'admin' };

    vi.mocked(apiClient.get).mockResolvedValue({ user: mockUser });

    const result = await auth.me();

    expect(result).toEqual(mockUser);
    expect(apiClient.get).toHaveBeenCalledWith('/session/me');
  });

  it('returns the unwrapped user from login response', async () => {
    const mockUser = { id: 'u-1', username: 'testuser', displayName: 'Test User', role: 'editor' };

    vi.mocked(apiClient.post).mockResolvedValue({ user: mockUser });

    const result = await auth.login('testuser', 'password123');

    expect(result).toEqual(mockUser);
    expect(apiClient.post).toHaveBeenCalledWith('/session/login', {
      username: 'testuser',
      password: 'password123',
    });
  });
});
