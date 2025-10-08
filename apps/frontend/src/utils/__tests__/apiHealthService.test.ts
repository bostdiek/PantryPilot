import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiHealthService, apiHealthService } from '../apiHealthService';

// Mock logger to avoid real console noise
vi.mock('../../lib/logger', () => ({
  logger: {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock offlineSync module
const mockHasPending = vi.fn();
const mockSyncPending = vi.fn();
vi.mock('../offlineSync', () => ({
  hasPendingRecipes: () => mockHasPending(),
  syncPendingRecipes: () => mockSyncPending(),
}));

// Helper to mock global fetch
function mockFetch(response: Partial<Response> | 'network-error') {
  if (response === 'network-error') {
    global.fetch = vi.fn(
      () => Promise.reject(new Error('Network')) as any
    ) as any;
    return;
  }

  const res = {
    ok: true,
    status: (response as any).status ?? 200,
    json: async () => ({ status: 'healthy' }),
  } as unknown as Response;

  // Return immediate resolved promise to avoid timing/timeouts
  global.fetch = vi.fn(() => Promise.resolve(res) as any) as any;
}

describe('ApiHealthService', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockHasPending.mockReset();
    mockSyncPending.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
    // stop any running interval on singleton
    apiHealthService.stop();
    // Restore original fetch if it was mocked by this test file
    if ((vi as any).mocked && typeof (vi as any).mocked === 'function') {
      // noop - keep compatibility with environments
    }
  });

  it('should treat 200 as online and notify subscribers', async () => {
    mockFetch({ status: 200 });

    const svc = new ApiHealthService(1000);
    const updates: boolean[] = [];
    svc.subscribe((online) => updates.push(online));

    await svc['checkHealth']();

    expect(updates[0]).toBe(true);
  });

  it('should mark offline on network error and notify subscribers', async () => {
    mockFetch('network-error');

    const svc = new ApiHealthService(1000);
    const updates: boolean[] = [];
    svc.subscribe((online) => updates.push(online));

    await svc['checkHealth']();

    expect(updates[updates.length - 1]).toBe(false);
  });

  it('should attempt sync when coming back online and pending recipes exist', async () => {
    // First call: network error -> offline
    const fetchMock1 = vi.fn(() => Promise.reject(new Error('Network')));
    // Second call: 200 OK -> online
    const res = {
      ok: true,
      status: 200,
      json: async () => ({ status: 'healthy' }),
    } as unknown as Response;
    const fetchMock2 = vi.fn(() => Promise.resolve(res));

    global.fetch = vi
      .fn()
      .mockImplementationOnce(fetchMock1 as any)
      .mockImplementationOnce(fetchMock2 as any) as unknown as typeof fetch;

    mockHasPending.mockReturnValue(true);
    mockSyncPending.mockResolvedValue({ synced: 2, failed: 0 });

    const svc = new ApiHealthService(1000);
    const updates: boolean[] = [];
    svc.subscribe((online) => updates.push(online));

    // First check -> offline
    await svc['checkHealth']();
    expect(updates[updates.length - 1]).toBe(false);

    // Second check -> online and triggers sync
    await svc['checkHealth']();

    expect(mockSyncPending).toHaveBeenCalled();
    expect(updates[updates.length - 1]).toBe(true);
  });
});
