import { useCallback, useState } from 'react';
import { useInterval, useMount } from 'react-use';
import { apiHealthService } from './apiHealthService';
import { getPendingRecipeCount, syncPendingRecipes } from './offlineSync';

/**
 * Hook to monitor API health and pending sync operations
 * @returns Object containing isApiOnline status and pendingItems count
 */
export function useApiHealth() {
  const [isApiOnline, setIsApiOnline] = useState<boolean>(true);
  const [pendingItems, setPendingItems] = useState<number>(0);

  // Handler for API status changes
  const handleApiStatusChange = useCallback(
    (isOnline: boolean) => {
      setIsApiOnline(isOnline);

      // If API just came back online and we have pending items, attempt to sync
      if (isOnline && pendingItems > 0) {
        syncPendingRecipes().then(() => {
          // Update pending items count after sync attempt
          setPendingItems(getPendingRecipeCount());
        });
      } else {
        // Still update pending count regularly
        setPendingItems(getPendingRecipeCount());
      }
    },
    [pendingItems]
  );

  // Check pending items function
  const checkPendingItems = useCallback(() => {
    setPendingItems(getPendingRecipeCount());
  }, []);

  // Initialize on mount
  useMount(() => {
    // Start API health monitoring
    apiHealthService.start();

    // Initialize pending items count
    checkPendingItems();
  });

  // Setup subscription after mount
  useMount(() => {
    return apiHealthService.subscribe(handleApiStatusChange);
  });

  // Periodic check for pending items
  useInterval(checkPendingItems, 60000); // Check every minute

  return { isApiOnline, pendingItems };
}
