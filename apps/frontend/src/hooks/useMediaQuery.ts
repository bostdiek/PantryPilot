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
        return () => {}; // No-op cleanup for SSR
      }

      const mediaQuery = window.matchMedia(query);

      // Add listener with fallback for older browsers
      if (mediaQuery.addEventListener) {
        mediaQuery.addEventListener('change', callback);
      } else {
        // Fallback for older browsers that don't support addEventListener
        mediaQuery.addListener(callback);
      }

      // Return cleanup function
      return () => {
        if (mediaQuery.removeEventListener) {
          mediaQuery.removeEventListener('change', callback);
        } else {
          // Fallback for older browsers
          mediaQuery.removeListener(callback);
        }
      };
    },
    () => {
      // Get current snapshot
      if (typeof window === 'undefined') {
        return false; // SSR fallback
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
