import { createRecipe } from '../api/endpoints/recipes';
import type { RecipeCreate } from '../types/Recipe';

/**
 * Attempts to sync any locally stored recipes with the backend
 * @returns {Promise<{synced: number, failed: number}>} - Counts of synced and failed recipes
 */
export type SyncResult = { synced: number; failed: number; error?: string };

export async function syncPendingRecipes(): Promise<SyncResult> {
  try {
    // Get pending recipes from localStorage
    const pendingRecipes = JSON.parse(
      localStorage.getItem('pendingRecipes') || '[]'
    ) as RecipeCreate[];
    if (pendingRecipes.length === 0) return { synced: 0, failed: 0 };

    // Try to sync each recipe
    const results = await Promise.allSettled(
      pendingRecipes.map((recipe: RecipeCreate) => createRecipe(recipe))
    );

    // Count successes and failures
    const synced = results.filter(
      (result) => result.status === 'fulfilled'
    ).length;
    const failed = results.filter(
      (result) => result.status === 'rejected'
    ).length;

    // Remove successfully synced recipes
    if (synced > 0) {
      const failedRecipes = pendingRecipes.filter(
        (_: RecipeCreate, index: number) => results[index].status === 'rejected'
      );
      localStorage.setItem('pendingRecipes', JSON.stringify(failedRecipes));
    }

    return { synced, failed };
  } catch (error) {
    console.error('Error syncing pending recipes:', error);
    return {
      synced: 0,
      failed: 0,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

/**
 * Checks if there are any pending recipes to be synced
 * @returns {boolean} - True if there are pending recipes
 */
export function hasPendingRecipes(): boolean {
  const pendingRecipes = JSON.parse(
    localStorage.getItem('pendingRecipes') || '[]'
  );
  return pendingRecipes.length > 0;
}

/**
 * Gets the count of pending recipes
 * @returns {number} - Number of pending recipes
 */
export function getPendingRecipeCount(): number {
  const pendingRecipes = JSON.parse(
    localStorage.getItem('pendingRecipes') || '[]'
  );
  return pendingRecipes.length;
}

/**
 * Save a recipe payload to localStorage for later sync.
 */
export function saveRecipeOffline(recipe: RecipeCreate) {
  const pendingRecipes = JSON.parse(
    localStorage.getItem('pendingRecipes') || '[]'
  ) as RecipeCreate[];
  pendingRecipes.push(recipe);
  localStorage.setItem('pendingRecipes', JSON.stringify(pendingRecipes));
}
