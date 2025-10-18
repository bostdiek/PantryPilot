import { useSyncExternalStore } from 'react';

/**
 * Custom hook to detect media query matches
 * Useful for responsive behavior in components
 *
 * @param query - The media query string to test
 * @returns boolean indicating if the media query matches
 *
 * @example
 * ```tsx
 * const isMobile = useMediaQuery('(max-width: 767px)');
 * const isDesktop = useMediaQuery('(min-width: 768px)');
 * ```
 */
export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (callback) => {
      // Check if we're in a browser environment
      if (typeof window === 'undefined') {
        // Server-side rendering - no-op cleanup
        return () => {};
      }

      // In some test environments window.matchMedia may not be defined
      const mm = (window as any).matchMedia;
      if (typeof mm !== 'function') {
        return () => {};
      }

      let mediaQuery: MediaQueryList;
      try {
        mediaQuery = window.matchMedia(query);
      } catch (err) {
        // If matchMedia throws (some envs), no-op
        // Use debug-level log to avoid lint complaints in test environments
        console.debug('useMediaQuery: matchMedia threw', err);
        return () => {};
      }

      // Add listener with fallback for older browsers
      if (mediaQuery.addEventListener) {
        mediaQuery.addEventListener('change', callback);
      } else if ((mediaQuery as any).addListener) {
        // Fallback for older browsers that don't support addEventListener
        (mediaQuery as any).addListener(callback);
      }

      // Return cleanup function
      return () => {
        try {
          if (mediaQuery.removeEventListener) {
            mediaQuery.removeEventListener('change', callback);
          } else if ((mediaQuery as any).removeListener) {
            (mediaQuery as any).removeListener(callback);
          }
        } catch {
          // ignore cleanup errors
        }
      };
    },
    () => {
      // Get current snapshot
      if (typeof window === 'undefined') {
        return false; // SSR fallback
      }
      // In some test environments window.matchMedia may not be defined
      // Fall back to false when unavailable to avoid throwing.
      if (typeof (window as any).matchMedia !== 'function') {
        return false;
      }
      return window.matchMedia(query).matches;
    },
    () => false // Server snapshot for SSR
  );
}

/**
 * Convenience hook to detect mobile viewports
 * Uses Tailwind's md breakpoint (768px) as the mobile/desktop boundary
 */
export function useIsMobile(): boolean {
  return useMediaQuery('(max-width: 767px)');
}

/**
 * Convenience hook to detect tablet viewports
 * Covers devices between mobile and desktop (768px - 1024px)
 */
export function useIsTablet(): boolean {
  return useMediaQuery('(min-width: 768px) and (max-width: 1024px)');
}

/**
 * Convenience hook to detect desktop viewports
 * Larger than tablet breakpoint (1024px+)
 */
export function useIsDesktop(): boolean {
  return useMediaQuery('(min-width: 1025px)');
}

/**
 * Convenience hook to detect touch-capable devices
 * Useful for enabling touch-specific interactions
 */
export function useIsTouchDevice(): boolean {
  return useMediaQuery('(pointer: coarse)');
}
