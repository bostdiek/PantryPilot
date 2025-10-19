import { render, waitFor } from '@testing-library/react';
import { useEffect, useState } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useImageSelection } from '../useImageSelection';

interface HookHarnessProps {
  files?: File[];
  onReport: (data: {
    selectedFiles: File[];
    previews: string[];
    error: string | null;
  }) => void;
}

function HookHarness({ files, onReport }: HookHarnessProps) {
  const [error, setError] = useState<string | null>(null);
  const hook = useImageSelection({ onError: setError });

  useEffect(() => {
    if (files) hook.processSelectedFiles(files);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [files]);

  useEffect(() => {
    onReport({
      selectedFiles: hook.selectedFiles,
      previews: hook.previews,
      error,
    });
  }, [hook.selectedFiles, hook.previews, error, onReport]);

  return null;
}

beforeEach(() => {
  (globalThis as any).URL.createObjectURL = vi.fn((input: any) => {
    if (input && input.name) return `blob:${input.name}`;
    return 'blob:test';
  });
  (globalThis as any).URL.revokeObjectURL = vi.fn();
});

describe('useImageSelection', () => {
  it('adds valid image files and generates previews', async () => {
    const fileA = new File(['fake-image-a'], 'a.jpg', { type: 'image/jpeg' });
    const fileB = new File(['fake-image-b'], 'b.png', { type: 'image/png' });

    const reports: any[] = [];
    render(
      <HookHarness files={[fileA, fileB]} onReport={(d) => reports.push(d)} />
    );

    await waitFor(() => {
      const last = reports[reports.length - 1];
      expect(last.selectedFiles.length).toBe(2);
      expect(last.previews.length).toBe(2);
      expect(last.error).toBeNull();
    });
  });

  it('rejects non-image files and reports error', async () => {
    const bad = new File(['not-an-image'], 'notes.txt', { type: 'text/plain' });

    const reports: any[] = [];
    render(<HookHarness files={[bad]} onReport={(d) => reports.push(d)} />);

    await waitFor(() => {
      const last = reports[reports.length - 1];
      expect(last.selectedFiles.length).toBe(0);
      expect(last.previews.length).toBe(0);
      expect(last.error).toMatch(/Please select only image files/i);
    });
  });
});
