import { type FC, useEffect, useRef } from 'react';

export interface ImageThumbnailProps {
  src?: string | null;
  loading?: boolean;
  error?: boolean;
  alt: string;
  index: number;
  selected?: boolean;
  onRemove: (index: number) => void;
  onFocusRequest?: (index: number) => void;
}
export const ImageThumbnail: FC<ImageThumbnailProps> = ({
  src,
  loading = false,
  error = false,
  alt,
  index,
  selected = false,
  onRemove,
  onFocusRequest,
}) => {
  const ref = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (selected) ref.current?.focus();
  }, [selected]);

  const imgAlt = `Preview of ${alt}`;
  // Validate image source to mitigate DOM-based XSS and excessive inline payloads.
  // Rules:
  // 1. Allow http/https and blob protocols (browser enforces same-origin / CSP policies).
  // 2. Allow data URIs ONLY for specific image MIME types (png, jpeg, webp, gif) and below a size threshold.
  // 3. Reject everything else (including javascript:, ftp:, file:, etc.).
  // 4. If parsing fails, treat as unsafe.
  const isSafeImageSrc = (value?: string | null): value is string => {
    if (!value) return false;
    let protocol: string;
    try {
      // Use window.location.href as base so relative URLs resolve correctly (still protocol http/https)
      const parsed = new URL(value, window.location.href);
      protocol = parsed.protocol.toLowerCase();
    } catch {
      return false;
    }

    if (protocol === 'http:' || protocol === 'https:' || protocol === 'blob:') {
      return true;
    }

    if (protocol === 'data:') {
      // Enforce MIME whitelist + size cap (approximate) to avoid huge inline payloads.
      // Example valid prefix: data:image/png;base64,iVBOR...
      const allowedMimePattern = /^data:image\/(png|jpe?g|webp|gif);base64,/i;
      if (!allowedMimePattern.test(value)) return false;
      // Rough size calculation: base64 expands ~4/3; compute bytes from length after comma.
      const commaIndex = value.indexOf(',');
      if (commaIndex === -1) return false;
      const base64Data = value.substring(commaIndex + 1);
      // Convert base64 length to bytes (ignoring padding nuances for simplicity).
      const estimatedBytes = Math.floor((base64Data.length * 3) / 4);
      // Cap inline images to ~1.5MB (tunable). Prevents unbounded memory usage.
      const MAX_INLINE_BYTES = 1.5 * 1024 * 1024; // 1.5 MiB
      if (estimatedBytes > MAX_INLINE_BYTES) return false;
      return true;
    }

    return false;
  };

  const safeSrc = isSafeImageSrc(src) ? src : undefined;
  return (
    <div className="group relative m-1">
      <button
        ref={ref}
        type="button"
        className={[
          'inline-flex h-28 w-28 items-center justify-center overflow-hidden rounded-md bg-gray-100',
          'transition duration-150',
          'group-hover:scale-105 group-hover:shadow-lg',
          selected ? 'ring-2 ring-blue-500' : '',
        ].join(' ')}
        style={{ touchAction: 'manipulation' }}
        onClick={() => onFocusRequest?.(index)}
        onFocus={() => onFocusRequest?.(index)}
      >
        {loading ? (
          <span
            className="h-8 w-8 animate-spin rounded-full border-4 border-blue-300 border-t-transparent"
            aria-label="Loading thumbnail"
          />
        ) : error ? (
          <span className="text-2xl text-red-500" aria-label="Thumbnail error">
            ⚠️
          </span>
        ) : // Only render the image when we have a validated safe src. If not, render nothing.
        safeSrc ? (
          <img
            src={safeSrc}
            alt={imgAlt}
            className="h-full w-full object-cover"
            onError={({ currentTarget }) => {
              (currentTarget as HTMLImageElement).style.display = 'none';
            }}
          />
        ) : null}
      </button>

      <button
        type="button"
        aria-label={`Remove ${index + 1}: ${alt || 'image'}`}
        onClick={() => onRemove(index)}
        className="absolute top-1 right-1 rounded bg-white p-1 text-sm opacity-80 shadow transition-opacity hover:opacity-100"
      >
        ✕
      </button>
    </div>
  );
};

export default ImageThumbnail;
