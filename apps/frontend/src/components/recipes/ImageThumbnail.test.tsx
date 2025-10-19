import '@testing-library/jest-dom';
import { fireEvent, render } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
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

describe('ImageThumbnail UI states & behaviors', () => {
  it('renders loading spinner when loading=true', () => {
    const { getByLabelText, queryByRole } = setup({ loading: true });
    expect(getByLabelText('Loading thumbnail')).toBeInTheDocument();
    // No image rendered during loading
    expect(queryByRole('img')).toBeNull();
  });

  it('renders error icon when error=true', () => {
    const { getByLabelText } = setup({ error: true });
    expect(getByLabelText('Thumbnail error')).toBeInTheDocument();
  });

  it('invokes onRemove with correct index', () => {
    const onRemove = vi.fn();
    const { getByRole } = setup({ src: tinyPng, onRemove, index: 3 });
    const btn = getByRole('button', { name: /Remove 4:/i }); // index is zero-based; aria-label adds +1
    fireEvent.click(btn);
    expect(onRemove).toHaveBeenCalledWith(3);
  });

  it('focuses itself when selected=true (accessibility focus management)', () => {
    const { getByRole } = setup({ src: tinyPng, selected: true });
    const thumbButton = getByRole('button', { name: /Preview of Test Image/i });
    expect(document.activeElement).toBe(thumbButton);
  });

  it('calls onFocusRequest when clicked', () => {
    const onFocusRequest = vi.fn();
    const { getByRole } = setup({ src: tinyPng, onFocusRequest });
    const thumbButton = getByRole('button', { name: /Preview of Test Image/i });
    fireEvent.click(thumbButton);
    expect(onFocusRequest).toHaveBeenCalledWith(0);
  });

  it('sanitizes alt text (removes angle brackets & newlines)', () => {
    const maliciousAlt = '<script>alert(1)</script>\nMulti\nLine';
    const { getByRole } = render(
      <ImageThumbnail
        alt={maliciousAlt}
        index={0}
        onRemove={() => {}}
        src={tinyPng}
      />
    );
    const img = getByRole('img');
    // Expect stripped angle brackets & newlines collapsed to spaces
    // The sanitizeAlt function strips < and > but leaves '/' characters intact.
    // So expected alt text preserves the slash between closing tag remnants.
    expect(img).toHaveAttribute(
      'alt',
      'Preview of scriptalert(1)/script Multi Line'
    );
  });
});
