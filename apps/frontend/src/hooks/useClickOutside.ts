import { useCallback, useEffect, useRef, type RefObject } from 'react';

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
): RefObject<T | null> {
  const ref = useRef<T>(null);
  // Track whether we should skip the current event (to avoid closing on the click that opened the modal)
  const skipNextEvent = useRef(false);

  const handleClickOutside = useCallback(
    (event: MouseEvent | TouchEvent) => {
      // Skip this event if we just became active (the opening click)
      if (skipNextEvent.current) {
        skipNextEvent.current = false;
        return;
      }

      const target = event.target as Node;

      // If ref is not set yet, don't trigger callback (element not mounted)
      if (!ref.current) {
        return;
      }

      // If click is inside the ref element, don't trigger callback
      if (ref.current.contains(target)) {
        return;
      }

      callback();
    },
    [callback]
  );

  useEffect(() => {
    if (!active) {
      return;
    }

    // Skip the first click event after becoming active to avoid closing on the opening click
    skipNextEvent.current = true;

    // Use bubble phase (default) to let interactive elements handle their clicks first
    // This prevents the outside click handler from closing modals before buttons can navigate
    document.addEventListener('click', handleClickOutside);
    document.addEventListener('touchend', handleClickOutside);

    return () => {
      document.removeEventListener('click', handleClickOutside);
      document.removeEventListener('touchend', handleClickOutside);
    };
  }, [handleClickOutside, active]);

  return ref;
}
