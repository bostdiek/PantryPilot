import { logger } from '../lib/logger';
import { hasPendingRecipes, syncPendingRecipes } from './offlineSync';

/**
 * Service to periodically check API health and sync pending data
 */
class ApiHealthService {
  private checkInterval: number | null = null;
  private healthEndpoint: string;
  private listeners: Array<(isOnline: boolean) => void> = [];
  private isOnline = true;
  /** Timeout for health-check requests in milliseconds. */
  private healthTimeoutMs: number;

  constructor(
    timeoutMs: number = Number(
      import.meta.env.VITE_API_HEALTH_TIMEOUT_MS ?? 5000
    )
  ) {
    // Respect deployment strategy: if VITE_API_URL is defined, use it.
    // Otherwise rely on same-origin reverse proxy routing.
    // We intentionally avoid defaulting to localhost in production so that
    // a production build running behind a proxy does not falsely report
    // offline status.
    const explicitBase = import.meta.env.VITE_API_URL?.trim();
    if (explicitBase) {
      this.healthEndpoint = `${explicitBase.replace(/\/$/, '')}/api/v1/health`;
    } else if (typeof window !== 'undefined') {
      this.healthEndpoint = `${window.location.origin}/api/v1/health`;
    } else {
      // SSR / non-browser fallback (retain prior localhost behavior only here)
      this.healthEndpoint = 'http://localhost:8000/api/v1/health';
    }
    this.healthTimeoutMs = timeoutMs;
  }

  /**
   * Start the health check service
   * @param intervalMs Interval in milliseconds (default: 30 seconds)
   */
  public start(intervalMs = 30000): void {
    if (this.checkInterval) {
      return; // Already running
    }

    // Do an initial check
    this.checkHealth();

    // Set up interval checking
    this.checkInterval = window.setInterval(() => {
      this.checkHealth();
    }, intervalMs);
  }

  /**
   * Stop the health check service
   */
  public stop(): void {
    if (this.checkInterval) {
      window.clearInterval(this.checkInterval);
      this.checkInterval = null;
    }
  }

  /**
   * Subscribe to API status changes
   * @param listener Function to call when status changes
   * @returns Unsubscribe function
   */
  public subscribe(listener: (isOnline: boolean) => void): () => void {
    this.listeners.push(listener);
    // Immediately notify with current status
    listener(this.isOnline);

    // Return unsubscribe function
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  /**
   * Check if the API is healthy and notify listeners of changes
   */
  private async checkHealth(): Promise<void> {
    try {
      const response = await fetch(this.healthEndpoint, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        signal: AbortSignal.timeout(this.healthTimeoutMs),
      });

      // Treat any successful fetch (including 401/403 auth required) as the API being ONLINE.
      // We only consider 5xx or network errors as offline conditions.
      const status = response.status;
      const newStatus = status < 500; // 1xx-4xx => online (API reachable)

      if (!newStatus) {
        logger.warn('Health check indicates server error status:', status);
      }

      // If coming back online, attempt pending sync.
      if (!this.isOnline && newStatus) {
        logger.info('API back online, attempting pending recipe sync');
        if (hasPendingRecipes()) {
          try {
            const result = await syncPendingRecipes();
            logger.info(
              `Synced ${result.synced} recipes, ${result.failed} failed`
            );
          } catch (err) {
            logger.error('Error syncing recipes:', err);
          }
        }
      }

      if (this.isOnline !== newStatus) {
        this.isOnline = newStatus;
        this.notifyListeners();
      }
    } catch (err) {
      // Network / timeout => offline
      if (this.isOnline) {
        logger.warn('Health check network error -> offline', err);
        this.isOnline = false;
        this.notifyListeners();
      }
    }
  }

  /**
   * Notify all listeners of the current status
   */
  private notifyListeners(): void {
    for (const listener of this.listeners) {
      listener(this.isOnline);
    }
  }
}

// Export singleton instance
export const apiHealthService = new ApiHealthService();

// Auto-start in browser environments
if (typeof window !== 'undefined') {
  apiHealthService.start();
}
