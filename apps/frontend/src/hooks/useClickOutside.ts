import { useCallback, useRef, useEffect, type RefObject } from 'react';

/**
 * More targeted hook for handling click outside events
 * Replaces generic useEffect patterns for modal dismissal
 *
 * @param callback - Function to call when clicking outside
 * @param active - Whether to listen for outside clicks (default: true)
 * @returns ref to attach to the element that should detect outside clicks
 *
 * @example
 * ```tsx
 * const modalRef = useClickOutside(() => setIsOpen(false), isOpen);
 * return <div ref={modalRef}>Modal content</div>
 * ```
 */
export function useClickOutside<T extends HTMLElement>(
  callback: () => void,
  active: boolean = true
): RefObject<T> {
  const ref = useRef<T>(null);

  const handleClickOutside = useCallback(
    (event: MouseEvent | TouchEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        callback();
      }
    },
    [callback]
  );

  useEffect(() => {
    if (!active) {
      return;
    }

    // Use capture phase to ensure we catch the event before other handlers
    document.addEventListener('mousedown', handleClickOutside, true);
    document.addEventListener('touchstart', handleClickOutside, true);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside, true);
      document.removeEventListener('touchstart', handleClickOutside, true);
    };
  }, [handleClickOutside, active]);

  return ref;
}
