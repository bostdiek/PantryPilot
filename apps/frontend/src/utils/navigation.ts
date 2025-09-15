/**
 * Centralized navigation helper used by components (e.g. ErrorBoundary) to
 * perform client-friendly navigation while remaining easy to mock in tests.
 *
 * In production it simply assigns to window.location.href. In tests, callers
 * can mock this function or provide a custom implementation. This isolates
 * test-specific concerns from UI components.
 */
export function navigateTo(url: string): void {
  if (typeof window === 'undefined' || !(window as any).location) return;
  try {
    (window as any).location.href = url;
  } catch {
    // Silently ignore navigation failures (e.g., jsdom limitations)
  }
}
