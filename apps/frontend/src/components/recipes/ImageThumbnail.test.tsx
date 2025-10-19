import { describe, it, expect } from 'vitest';
import '@testing-library/jest-dom';
import { render } from '@testing-library/react';
import ImageThumbnail, { type ImageThumbnailProps } from './ImageThumbnail';

// Helper to render component
const setup = (props: Partial<ImageThumbnailProps>) => {
  return render(
    <ImageThumbnail alt="Test Image" index={0} onRemove={() => {}} {...props} />
  );
};

// A minimal small valid PNG data URI (1x1 transparent pixel)
const tinyPng =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8CAAAMBAQDJpZtNAAAAAElFTkSuQmCC';

// Oversized data URI (simulate ~2MB). We'll just repeat tiny png base64 until size exceeds limit.
const bigData =
  'data:image/png;base64,' + 'A'.repeat(Math.ceil((1.6 * 1024 * 1024 * 4) / 3));

// Invalid MIME
const invalidMime = 'data:image/svg+xml;base64,PHN2ZyB4bWxu...';

// Wrong protocol
const jsProto = 'javascript:alert(1)';

// Blob/http/https examples (we only test that they render attempt; we can't fabricate real blobs easily here).
const httpUrl = 'https://example.com/image.png';

describe('ImageThumbnail safe src validation', () => {
  it('renders valid png data URI', () => {
    setup({ src: tinyPng });
    // Image should exist
    expect(document.querySelector('img')?.getAttribute('src')).toBe(tinyPng);
  });

  it('rejects oversized data URI', () => {
    setup({ src: bigData });
    expect(document.querySelector('img')).toBeNull();
  });

  it('rejects invalid MIME data URI', () => {
    setup({ src: invalidMime });
    expect(document.querySelector('img')).toBeNull();
  });

  it('rejects javascript protocol', () => {
    setup({ src: jsProto });
    expect(document.querySelector('img')).toBeNull();
  });

  it('allows https URL', () => {
    setup({ src: httpUrl });
    expect(document.querySelector('img')?.getAttribute('src')).toBe(httpUrl);
  });
});
