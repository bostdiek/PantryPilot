import { useEffect, useState } from 'react';
import {
  groceryListsApi,
  type GroceryListIngredient,
  type GroceryListRequest,
} from '../api/endpoints/groceryLists';
import { Stack } from '../components/layout';
import { Button, Card, Container, LoadingSpinner } from '../components/ui';
import { useApi } from '../hooks/useApi';

/**
 * Generates CSV content from grocery list ingredients
 */
function generateCSV(ingredients: GroceryListIngredient[]): string {
  const headers = ['Ingredient', 'Quantity', 'Unit', 'Recipes'];
  const rows = ingredients.map((ingredient) => [
    ingredient.name,
    ingredient.quantity_value.toString(),
    ingredient.quantity_unit,
    ingredient.recipes.join('; '),
  ]);

  const csvContent = [headers, ...rows]
    .map((row) =>
      row.map((field) => {
        // Escape quotes and wrap in quotes if field contains comma, quote, or newline
        if (
          field.includes(',') ||
          field.includes('"') ||
          field.includes('\n')
        ) {
          return `"${field.replace(/"/g, '""')}"`;
        }
        return field;
      })
    )
    .map((row) => row.join(','))
    .join('\n');

  return csvContent;
}

/**
 * Downloads CSV content as a file
 */
function downloadCSV(csvContent: string, filename: string): void {
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);

  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  URL.revokeObjectURL(url);
}

/**
 * Gets the current week's start and end dates (Sunday to Saturday)
 */
function getCurrentWeekDates(): { startDate: string; endDate: string } {
  const today = new Date();
  const dayOfWeek = today.getDay(); // 0 = Sunday, 1 = Monday, etc.

  // Calculate Sunday of current week
  const startDate = new Date(today);
  startDate.setDate(today.getDate() - dayOfWeek);

  // Calculate Saturday of current week
  const endDate = new Date(startDate);
  endDate.setDate(startDate.getDate() + 6);

  return {
    startDate: startDate.toISOString().split('T')[0],
    endDate: endDate.toISOString().split('T')[0],
  };
}

function GroceryListPage() {
  const { startDate: defaultStartDate, endDate: defaultEndDate } =
    getCurrentWeekDates();

  const [startDate, setStartDate] = useState(defaultStartDate);
  const [endDate, setEndDate] = useState(defaultEndDate);

  const {
    data: groceryList,
    loading,
    error,
    execute: generateGroceryList,
  } = useApi(groceryListsApi.generateGroceryList);

  // Auto-load grocery list when the selected date range changes.
  // include generateGroceryList in deps to satisfy exhaustive-deps
  useEffect(() => {
    // Avoid running on mount if dates are invalid
    if (!startDate || !endDate) return;

    const request: GroceryListRequest = {
      start_date: startDate,
      end_date: endDate,
    };

    // Fire-and-forget; errors are handled by the hook and UI
    generateGroceryList(request).catch((err) => {
      // Keep console.error for local debugging; UI shows error state via `error` from the hook
      console.error('Failed to generate initial grocery list:', err);
    });
  }, [startDate, endDate, generateGroceryList]);

  const handleGenerateList = async () => {
    const request: GroceryListRequest = {
      start_date: startDate,
      end_date: endDate,
    };

    try {
      await generateGroceryList(request);
    } catch (err) {
      console.error('Failed to generate grocery list:', err);
    }
  };

  const handleExportCSV = () => {
    if (!groceryList?.ingredients) {
      return;
    }

    const csvContent = generateCSV(groceryList.ingredients);
    const filename = `grocery-list-${startDate}-to-${endDate}.csv`;
    downloadCSV(csvContent, filename);
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const formatQuantity = (value: number): string => {
    // Format to remove unnecessary decimal places
    return value % 1 === 0
      ? value.toString()
      : value.toFixed(2).replace(/\.?0+$/, '');
  };

  return (
    <Container size="lg">
      <Stack gap={6}>
        {/* Page header */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Grocery List</h1>
        </div>

        {/* Date selection and generation */}
        <Card variant="default">
          <div className="p-6">
            <h2 className="mb-4 text-lg font-semibold">
              Generate Grocery List
            </h2>

            <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="flex flex-col">
                <label
                  htmlFor="start-date"
                  className="mb-1 text-sm font-medium text-gray-700"
                >
                  Start Date
                </label>
                <input
                  id="start-date"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-base transition-colors outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="flex flex-col">
                <label
                  htmlFor="end-date"
                  className="mb-1 text-sm font-medium text-gray-700"
                >
                  End Date
                </label>
                <input
                  id="end-date"
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-base transition-colors outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="flex justify-end">
              <Button
                variant="primary"
                onClick={handleGenerateList}
                disabled={loading || !startDate || !endDate}
              >
                {loading ? 'Updating...' : 'Update Grocery List'}
              </Button>
            </div>
          </div>
        </Card>

        {/* Loading state */}
        {loading && (
          <Card variant="default">
            <div className="flex justify-center py-12">
              <LoadingSpinner />
            </div>
          </Card>
        )}

        {/* Error state */}
        {error && (
          <Card variant="default">
            <div className="p-6 text-center">
              <p className="mb-4 text-red-500">
                Failed to generate grocery list: {error.message}
              </p>
              <Button variant="secondary" onClick={handleGenerateList}>
                Try Again
              </Button>
            </div>
          </Card>
        )}

        {/* Grocery list results */}
        {groceryList && !loading && (
          <Card variant="default">
            <div className="p-6">
              <div className="mb-6 flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold">Your Grocery List</h2>
                  <p className="text-sm text-gray-600">
                    {formatDate(groceryList.start_date)} -{' '}
                    {formatDate(groceryList.end_date)}
                  </p>
                  <p className="text-sm text-gray-600">
                    Based on {groceryList.total_meals} planned meal
                    {groceryList.total_meals !== 1 ? 's' : ''}
                  </p>
                </div>

                {groceryList.ingredients.length > 0 && (
                  <Button variant="secondary" onClick={handleExportCSV}>
                    Export CSV
                  </Button>
                )}
              </div>

              {groceryList.ingredients.length === 0 ? (
                <div className="py-8 text-center">
                  <p className="text-lg text-gray-500">No ingredients found</p>
                  <p className="mt-2 text-sm text-gray-400">
                    Try selecting a different date range or adding recipes to
                    your meal plan.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
                          Ingredient
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
                          Quantity
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
                          Used In
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 bg-white">
                      {groceryList.ingredients.map((ingredient) => (
                        <tr key={ingredient.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm font-medium text-gray-900">
                              {ingredient.name}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm text-gray-900">
                              {formatQuantity(ingredient.quantity_value)}{' '}
                              {ingredient.quantity_unit}
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="text-sm text-gray-900">
                              {ingredient.recipes.join(', ')}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </Card>
        )}
      </Stack>
    </Container>
  );
}

export default GroceryListPage;
