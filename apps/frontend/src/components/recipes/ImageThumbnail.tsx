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
  // Only allow safe image source schemes to prevent DOM-based XSS via javascript: URIs
  const isSafeImageSrc = (value?: string | null): value is string => {
    if (!value) return false;
    try {
      // Attempt to parse as URL to get protocol when possible
      // For data: and blob: URLs, URL constructor works in modern browsers
      const parsed = new URL(value, window.location.href);
      const protocol = parsed.protocol.toLowerCase();
      return (
        protocol === 'http:' ||
        protocol === 'https:' ||
        protocol === 'blob:' ||
        protocol === 'data:'
      );
    } catch {
      // If URL parsing fails, reject the value as unsafe
      return false;
    }
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
