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

  return (
    <div className="group relative m-1">
      <button
        ref={ref}
        type="button"
        aria-pressed={selected}
        aria-label={`Preview ${index + 1}: ${alt}`}
        className={[
          'flex h-24 min-h-[48px] w-24 min-w-[48px] items-center justify-center overflow-hidden rounded bg-gray-100 focus:ring-2 focus:ring-blue-500 focus:outline-none',
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
        ) : (
          <img
            src={src ?? undefined}
            alt={imgAlt}
            className="h-full w-full object-cover"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
            }}
          />
        )}
      </button>
      <button
        type="button"
        aria-label={`Remove ${index + 1}`}
        onClick={() => onRemove(index)}
        className="absolute top-1 right-1 rounded bg-white p-1 text-sm opacity-80 shadow transition-opacity hover:opacity-100"
      >
        ✕
      </button>
    </div>
  );
};

export default ImageThumbnail;
