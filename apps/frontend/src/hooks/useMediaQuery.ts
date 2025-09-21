import { useEffect, useState } from 'react';

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
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    // Check if we're in a browser environment
    if (typeof window === 'undefined') {
      return;
    }

    const mediaQuery = window.matchMedia(query);
    
    // Set initial value
    setMatches(mediaQuery.matches);

    // Create event listener function
    const handleChange = (event: MediaQueryListEvent) => {
      setMatches(event.matches);
    };

    // Add listener
    mediaQuery.addEventListener('change', handleChange);

    // Cleanup
    return () => {
      mediaQuery.removeEventListener('change', handleChange);
    };
  }, [query]);

  return matches;
}

/**
 * Convenience hook to detect mobile viewports
 * Uses Tailwind's md breakpoint (768px) as the mobile/desktop boundary
 */
export function useIsMobile(): boolean {
  return useMediaQuery('(max-width: 767px)');
}