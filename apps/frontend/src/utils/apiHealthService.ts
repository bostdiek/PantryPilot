import { hasPendingRecipes, syncPendingRecipes } from './offlineSync';

/**
 * Service to periodically check API health and sync pending data
 */
class ApiHealthService {
  private checkInterval: number | null = null;
  private apiUrl: string;
  private listeners: Array<(isOnline: boolean) => void> = [];
  private isOnline = true;
  /** Timeout for health-check requests in milliseconds. */
  private healthTimeoutMs: number;

  constructor(
    timeoutMs: number = Number(
      import.meta.env.VITE_API_HEALTH_TIMEOUT_MS ?? 5000
    )
  ) {
    this.apiUrl = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/health`;
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
      const response = await fetch(this.apiUrl, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        // Short timeout to avoid long waits
        signal: AbortSignal.timeout(this.healthTimeoutMs),
      });

      const newStatus = response.ok;

      // If status changed from offline to online
      if (!this.isOnline && newStatus) {
        console.log('API back online, checking for pending recipes to sync');
        // Check if there are pending recipes to sync
        if (hasPendingRecipes()) {
          try {
            const result = await syncPendingRecipes();
            console.log(
              `Synced ${result.synced} recipes, ${result.failed} failed`
            );
          } catch (err) {
            console.error('Error syncing recipes:', err);
          }
        }
      }

      // Only notify listeners if status changed
      if (this.isOnline !== newStatus) {
        this.isOnline = newStatus;
        this.notifyListeners();
      }
    } catch {
      // If we caught an error, API is offline
      if (this.isOnline) {
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
