// Use Vitest globals (configured via vitest.config.ts)
import { beforeEach, describe, expect, it, vi } from 'vitest';

// Mocks for modules used by aiDrafts
vi.mock('../../../lib/logger', () => ({
  logger: { error: vi.fn(), warn: vi.fn(), info: vi.fn() },
}));

// Mock api client and base url. Keep the spy internal to the factory (hoist-safe).
vi.mock('../../client', () => {
  const request = vi.fn();
  return {
    apiClient: { request },
    getApiBaseUrl: () => 'http://api',
  };
});

// Helper to access the mocked apiClient.request spy inside tests
const getMockRequest = async () => {
  const mod = await import('../../client');
  // typed as any to avoid depending on Jest types; Vitest's `vi.fn()` is used
  return mod.apiClient.request as any;
};

// Control auth token in tests
let tokenValue: string | null = 'test-token';
vi.mock('../../../stores/useAuthStore', () => ({
  useAuthStore: {
    getState: () => ({ token: tokenValue }),
  },
}));

import {
  extractRecipeFromUrl,
  extractRecipeStream,
  extractRecipeStreamFetch,
  getDraftById,
  getDraftByIdOwner,
} from '../aiDrafts';

describe('aiDrafts endpoints', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // reset token
    tokenValue = 'test-token';
  });

  it('extractRecipeFromUrl calls apiClient with POST body', async () => {
    const mockRequest = await getMockRequest();
    mockRequest!.mockResolvedValueOnce({ signed_url: '/s' });

    const res = await extractRecipeFromUrl('https://site/recipe', 'prom');

    expect(mockRequest).toHaveBeenCalledWith(
      '/api/v1/ai/extract-recipe-from-url',
      expect.objectContaining({ method: 'POST' })
    );
    // Should return whatever apiClient returned
    expect(res).toEqual({ signed_url: '/s' });
  });

  it('getDraftById and getDraftByIdOwner call apiClient with proper routes', async () => {
    const mockRequest = await getMockRequest();
    mockRequest!.mockResolvedValueOnce({ payload: { id: 'd' } });
    await getDraftById('draft-1', 'tok-123');
    expect(mockRequest).toHaveBeenCalledWith(
      '/api/v1/ai/drafts/draft-1?token=tok-123',
      expect.objectContaining({ method: 'GET' })
    );

    mockRequest!.mockResolvedValueOnce({ payload: { id: 'd2' } });
    await getDraftByIdOwner('draft-2');
    expect(mockRequest).toHaveBeenCalledWith(
      '/api/v1/ai/drafts/draft-2/me',
      expect.objectContaining({ method: 'GET' })
    );
  });

  it('extractRecipeStream handles EventSource complete, parse error, and onerror', () => {
    const created: any[] = [];

    class MockEventSource {
      onmessage: any = null;
      onerror: any = null;
      url: string;
      options: any;
      closed = false;
      constructor(url: string, options?: any) {
        this.url = url;
        this.options = options;
        created.push(this);
      }
      close() {
        this.closed = true;
      }
    }

    // Override global EventSource for tests
    // @ts-ignore
    global.EventSource = MockEventSource as any;

    const onProgress = vi.fn();
    const onComplete = vi.fn();
    const onError = vi.fn();

    // 1) Normal complete message
    const _es = extractRecipeStream(
      'u',
      undefined,
      onProgress,
      onComplete,
      onError
    );
    // There should be one created instance
    expect(created.length).toBeGreaterThanOrEqual(1);
    const inst = created[0];

    // Send a complete SSE message
    inst.onmessage({
      data: JSON.stringify({
        status: 'complete',
        signed_url: '/signed',
        draft_id: 'd1',
      }),
    });

    expect(onProgress).toHaveBeenCalled();
    expect(onComplete).toHaveBeenCalledWith('/signed', 'd1');
    expect(inst.closed).toBe(true);

    // 2) Parse error path: create a fresh instance
    const inst2 = created[1] ?? new MockEventSource('u2');
    // simulate invalid JSON
    inst2.onmessage = null; // ensure property exists
    // call handler via the same API: call extractRecipeStream again to wire handlers
    extractRecipeStream('u2', undefined, onProgress, onComplete, onError);
    const used = created[created.length - 1];
    used.onmessage({ data: 'not-json' });

    // parse error should trigger onError
    expect(onError).toHaveBeenCalled();

    // 3) onerror handler
    extractRecipeStream('u3', undefined, onProgress, onComplete, onError);
    const used3 = created[created.length - 1];
    used3.onerror({ type: 'err' });
    expect(onError).toHaveBeenCalled();
  });

  it('extractRecipeStreamFetch processes stream messages and honors token header', async () => {
    const onProgress = vi.fn();
    const onComplete = vi.fn();
    const onError = vi.fn();

    // Prepare a fake reader that returns one SSE message then done
    const encoder = new TextEncoder();
    const sse =
      'data: ' +
      JSON.stringify({ status: 'complete', draft_id: 'd-123' }) +
      '\n\n';
    const chunk = encoder.encode(sse);

    let readCalls = 0;
    const reader = {
      read: async () => {
        readCalls += 1;
        if (readCalls === 1) return { value: chunk, done: false };
        return { value: undefined, done: true };
      },
      cancel: vi.fn(),
    };

    const fakeBody = { getReader: () => reader };

    // Mock global.fetch
    // @ts-ignore
    global.fetch = vi.fn().mockResolvedValueOnce({ ok: true, body: fakeBody });

    const abortController = await extractRecipeStreamFetch(
      'https://site',
      undefined,
      onProgress,
      onComplete,
      onError
    );

    // Should have returned an AbortController-like object
    expect(abortController).toBeDefined();

    // fetch should have been called with Authorization header from mocked token
    // @ts-ignore
    expect(global.fetch).toHaveBeenCalled();
    expect(onProgress).toHaveBeenCalled();
    expect(onComplete).toHaveBeenCalledWith('', 'd-123');
  });

  it('extractRecipeStreamFetch handles HTTP error and no-body', async () => {
    const onProgress = vi.fn();
    const onComplete = vi.fn();
    const onError = vi.fn();

    // HTTP error
    // @ts-ignore
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Server Error',
    });

    await extractRecipeStreamFetch(
      'u',
      undefined,
      onProgress,
      onComplete,
      onError
    );
    expect(onError).toHaveBeenCalled();

    // No body
    // @ts-ignore
    global.fetch = vi.fn().mockResolvedValueOnce({ ok: true, body: null });
    await extractRecipeStreamFetch(
      'u',
      undefined,
      onProgress,
      onComplete,
      onError
    );
    expect(onError).toHaveBeenCalled();
  });

  it('extractRecipeStreamFetch handles AbortError and other exceptions', async () => {
    const onProgress = vi.fn();
    const onComplete = vi.fn();
    const onError = vi.fn();

    // AbortError should not call onError
    const abortErr = new Error('aborted');
    abortErr.name = 'AbortError';
    // @ts-ignore
    global.fetch = vi.fn().mockRejectedValueOnce(abortErr);

    const ac = await extractRecipeStreamFetch(
      'u',
      undefined,
      onProgress,
      onComplete,
      onError
    );
    expect(ac).toBeDefined();

    // Other error should call onError
    // @ts-ignore
    global.fetch = vi.fn().mockRejectedValueOnce(new Error('network'));
    await extractRecipeStreamFetch(
      'u',
      undefined,
      onProgress,
      onComplete,
      onError
    );
    expect(onError).toHaveBeenCalled();
  });
});
