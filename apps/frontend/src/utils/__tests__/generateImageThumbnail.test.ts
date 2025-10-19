import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { generateImageThumbnail } from '../generateImageThumbnail';

describe('generateImageThumbnail', () => {
  let originalCreateImageBitmap: any;
  let origCreateElement: any;

  beforeEach(() => {
    originalCreateImageBitmap = (global as any).createImageBitmap;
    origCreateElement = document.createElement.bind(document);
  });

  afterEach(() => {
    (global as any).createImageBitmap = originalCreateImageBitmap;
    document.createElement = origCreateElement;
    vi.restoreAllMocks();
  });

  it('returns null when createImageBitmap throws', async () => {
    (global as any).createImageBitmap = vi.fn(() => {
      throw new Error('nope');
    });

    const file = new File(['x'], 'x.jpg', { type: 'image/jpeg' });
    const result = await generateImageThumbnail(file, 100);
    expect(result).toBeNull();
  });

  it('creates a thumbnail blob when canvas and image bitmap are available', async () => {
    // Mock createImageBitmap to return a simple object with width/height and close
    (global as any).createImageBitmap = vi.fn().mockResolvedValue({
      width: 400,
      height: 200,
      close: vi.fn(),
    });

    // Mock canvas behavior: returned element has getContext and toBlob
    document.createElement = ((tag: string) => {
      if (tag === 'canvas') {
        return {
          width: 0,
          height: 0,
          getContext: () => ({ drawImage: () => {} }),
          toBlob: (cb: (b: Blob | null) => void) =>
            cb(new Blob(['thumb'], { type: 'image/jpeg' })),
        } as unknown as HTMLCanvasElement;
      }
      return origCreateElement(tag);
    }) as any;

    const file = new File(['x'], 'x.jpg', { type: 'image/jpeg' });
    const result = await generateImageThumbnail(file, 150);
    expect(result).toBeInstanceOf(Blob);
    // Ensure createImageBitmap was called
    expect((global as any).createImageBitmap).toHaveBeenCalled();
  });
});
