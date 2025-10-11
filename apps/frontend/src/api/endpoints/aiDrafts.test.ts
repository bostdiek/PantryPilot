import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorImpl } from '../../types/api';
import {
  extractRecipeFromImage,
  extractRecipeFromImageStream,
  extractRecipeStreamFetch,
  isSafeInternalPath,
} from './aiDrafts';

// Helpers to build a mock ReadableStream reader
function makeReaderFromChunks(chunks: string[], _doneIndex = chunks.length) {
  const encoder = new TextEncoder();
  const buffers = chunks.map((c) => encoder.encode(c));
  let i = 0;
  return {
    read: async () => {
      // Return each chunk with done=false so the consumer processes it.
      if (i < buffers.length) {
        const value = buffers[i++];
        return { value, done: false } as any;
      }
      // After all chunks are returned, signal done
      return { value: undefined, done: true } as any;
    },
    cancel: vi.fn(),
  };
}

describe('aiDrafts helpers', () => {
  it('validates safe internal paths correctly', () => {
    // same origin and starts with /recipes
    expect(isSafeInternalPath('/recipes/123')).toBe(true);

    // absolute same-origin
    const origin = window.location.origin;
    expect(isSafeInternalPath(`${origin}/recipes/new`)).toBe(true);

    // other origin
    expect(isSafeInternalPath('https://example.com/recipes/1')).toBe(false);

    // wrong path
    expect(isSafeInternalPath('/other/path')).toBe(false);

    // invalid url
    expect(isSafeInternalPath('not a url')).toBe(false);
  });
});

describe('extractRecipeStreamFetch', () => {
  const realFetch = global.fetch;

  beforeEach(() => {
    vi.useRealTimers();
  });

  afterEach(() => {
    global.fetch = realFetch as any;
    vi.resetAllMocks();
  });

  it('handles no body in response', async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({ ok: true, body: null });

    const onProgress = vi.fn();
    const onComplete = vi.fn();
    const onError = vi.fn();

    const controller = await extractRecipeStreamFetch(
      'https://example.com',
      undefined,
      onProgress,
      onComplete,
      onError
    );

    expect(controller).toBeDefined();
    expect(onError).toHaveBeenCalled();
  });

  it('parses SSE stream and calls onComplete on complete message', async () => {
    // Build fake reader that yields an SSE message 'data: {...}\n\n'
    const sse =
      'data: {"status":"progress","detail":"50%"}\n\n' +
      'data: {"status":"complete","draft_id":"abc-123"}\n\n';

    const reader = makeReaderFromChunks([sse]);

    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      body: {
        getReader: () => reader,
        getReaderOriginal: () => reader,
      } as any,
    });

    const onProgress = vi.fn();
    const onComplete = vi.fn();
    const onError = vi.fn();

    const controller = await extractRecipeStreamFetch(
      'https://example.com',
      undefined,
      onProgress,
      onComplete,
      onError
    );

    expect(onProgress).toHaveBeenCalled();
    expect(onComplete).toHaveBeenCalledWith('', 'abc-123');
    expect(onError).not.toHaveBeenCalled();
    expect(controller).toBeDefined();
  });

  it('reports HTTP error responses', async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 500, statusText: 'Boom' });

    const onProgress = vi.fn();
    const onComplete = vi.fn();
    const onError = vi.fn();

    await extractRecipeStreamFetch(
      'https://example.com',
      undefined,
      onProgress,
      onComplete,
      onError
    );

    expect(onError).toHaveBeenCalled();
  });
});

describe('extractRecipeFromImageStream & extractRecipeFromImage', () => {
  const realFetch = global.fetch;

  afterEach(() => {
    global.fetch = realFetch as any;
    vi.resetAllMocks();
  });

  it('extractRecipeFromImage throws on 413/415 errors', async () => {
    const file = new File(['x'], 'photo.jpg', { type: 'image/jpeg' });

    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: false,
      status: 413,
      statusText: 'Too Large',
    });

    await expect(extractRecipeFromImage(file)).rejects.toBeInstanceOf(
      ApiErrorImpl
    );
  });

  it('extractRecipeFromImageStream handles upload then streaming complete', async () => {
    const file = new File(['x'], 'photo.jpg', { type: 'image/jpeg' });

    // First call: uploadResponse
    const uploadBody = {
      data: { draft_id: 'd1', signed_url: 'https://signed' },
    };
    // Second call: stream response with SSE data
    const sse = 'data: {"status":"complete"}\n\n';
    const reader = makeReaderFromChunks([sse]);

    // Mock upload response.json
    const uploadResponse = {
      ok: true,
      json: async () => uploadBody,
    } as any;

    // Mock stream response
    const streamResponse = {
      ok: true,
      body: { getReader: () => reader } as any,
    } as any;

    global.fetch = vi
      .fn()
      .mockResolvedValueOnce(uploadResponse)
      .mockResolvedValueOnce(streamResponse);

    const onProgress = vi.fn();
    const onComplete = vi.fn();
    const onError = vi.fn();

    const controller = await extractRecipeFromImageStream(
      file,
      onProgress,
      onComplete,
      onError
    );

    expect(onProgress).toHaveBeenCalled();
    expect(onComplete).toHaveBeenCalledWith('https://signed', 'd1');
    expect(onError).not.toHaveBeenCalled();
    expect(controller).toBeDefined();
  });
});
