import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useImageSelection } from './useImageSelection';

// Mock thumbnail generator to exercise both success & failure paths
const mockGenerate = vi.fn();
vi.mock('../utils/generateImageThumbnail', () => ({
  generateImageThumbnail: (...args: any[]) => mockGenerate(...args),
}));

// Provide URL objectURL utilities
beforeEach(() => {
  (global as any).URL = (global as any).URL || {};
  (global as any).URL.createObjectURL = vi
    .fn()
    .mockImplementation((blob: any) => `blob:${blob?.name || 'x'}`);
  (global as any).URL.revokeObjectURL = vi.fn();
  mockGenerate.mockReset();
});

function makeFile(name: string, size: number, type = 'image/png'): File {
  const blob = new Blob([new Uint8Array(size)], { type });
  return new File([blob], name, { type });
}

describe('useImageSelection', () => {
  it('adds valid image file and eventually creates preview (fallback path when thumbnail fails)', async () => {
    mockGenerate.mockRejectedValue(new Error('thumb fail'));
    const onError = vi.fn();
    const { result } = renderHook(() => useImageSelection({ onError }));
    const file = makeFile('a.png', 10_000);
    act(() => {
      result.current.processSelectedFiles([file]);
    });
    expect(result.current.selectedFiles).toHaveLength(1);
    // Preview generation is async; wait a tick
    await waitFor(() => {
      expect(result.current.previews.length).toBe(1);
    });
    expect(onError).toHaveBeenCalledWith(null); // cleared error
  });

  it('rejects invalid MIME types', () => {
    const onError = vi.fn();
    const { result } = renderHook(() => useImageSelection({ onError }));
    const bad = makeFile('script.txt', 1000, 'text/plain');
    act(() => {
      result.current.processSelectedFiles([bad]);
    });
    expect(result.current.selectedFiles).toHaveLength(0);
    expect(onError).toHaveBeenCalled();
    const msg = onError.mock.calls[0][0];
    expect(String(msg)).toMatch(/Please select only image files/i);
  });

  it('rejects oversized file', () => {
    const onError = vi.fn();
    const { result } = renderHook(() =>
      useImageSelection({ onError, perFileLimit: 1_000 })
    );
    const big = makeFile('big.png', 2_000);
    act(() => {
      result.current.processSelectedFiles([big]);
    });
    expect(result.current.selectedFiles).toHaveLength(0);
    expect(onError).toHaveBeenCalled();
    expect(onError.mock.calls[0][0]).toMatch(/File size too large/i);
  });

  it('rejects when combined size exceeds limit', () => {
    const onError = vi.fn();
    const { result } = renderHook(() =>
      useImageSelection({ onError, combinedSizeLimit: 5_000 })
    );
    const f1 = makeFile('1.png', 3_000);
    const f2 = makeFile('2.png', 3_000);
    act(() => {
      result.current.processSelectedFiles([f1]);
    });
    act(() => {
      result.current.processSelectedFiles([f2]);
    });
    expect(result.current.selectedFiles).toHaveLength(1); // second rejected
    expect(onError).toHaveBeenCalled();
    const msgs = onError.mock.calls.map((c) => c[0]).join(' | ');
    expect(msgs).toMatch(/Combined file size/i);
  });

  it('removes a file and revokes its object URL after previews ready', async () => {
    const onError = vi.fn();
    mockGenerate.mockResolvedValue(
      new Blob([new Uint8Array(10_000)], { type: 'image/png' })
    );
    const { result } = renderHook(() => useImageSelection({ onError }));
    const f1 = makeFile('one.png', 2_000);
    const f2 = makeFile('two.png', 2_000);
    act(() => {
      result.current.processSelectedFiles([f1, f2]);
    });
    await waitFor(() => {
      expect(result.current.previews.length).toBe(2);
    });
    expect(result.current.selectedFiles).toHaveLength(2);
    const firstPreview = result.current.previews[0];
    act(() => {
      result.current.removeFile(0);
    });
    expect(result.current.selectedFiles).toHaveLength(1);
    expect((global as any).URL.revokeObjectURL).toHaveBeenCalledWith(
      firstPreview
    );
  });

  it('clears all files and previews', async () => {
    mockGenerate.mockRejectedValue(new Error('fail')); // exercise fallback again
    const { result } = renderHook(() => useImageSelection());
    const f = makeFile('x.png', 1000);
    act(() => {
      result.current.processSelectedFiles([f]);
    });
    await waitFor(() => {
      expect(result.current.selectedFiles).toHaveLength(1);
      expect(result.current.previews.length).toBe(1);
    });
    act(() => {
      result.current.clearAll();
    });
    expect(result.current.selectedFiles).toHaveLength(0);
    expect(result.current.previews.length).toBe(0);
  });
});
