import { useState } from 'react';
import { Container, Card, Button, LoadingSpinner } from '../components/ui';
import { Stack } from '../components/layout';
import { useApi } from '../hooks/useApi';
import {
  groceryListsApi,
  type GroceryListRequest,
  type GroceryListIngredient,
} from '../api/endpoints/groceryLists';

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
        if (field.includes(',') || field.includes('"') || field.includes('\n')) {
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
  const { startDate: defaultStartDate, endDate: defaultEndDate } = getCurrentWeekDates();
  
  const [startDate, setStartDate] = useState(defaultStartDate);
  const [endDate, setEndDate] = useState(defaultEndDate);

  const {
    data: groceryList,
    loading,
    error,
    execute: generateGroceryList,
  } = useApi(groceryListsApi.generateGroceryList);

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
    return value % 1 === 0 ? value.toString() : value.toFixed(2).replace(/\.?0+$/, '');
  };

  return (
    <Container size="lg">
      <Stack spacing="lg">
        {/* Page header */}
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Grocery List</h1>
        </div>

        {/* Date selection and generation */}
        <Card variant="default">
          <div className="p-6">
            <h2 className="text-lg font-semibold mb-4">Generate Grocery List</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
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
                  className="w-full rounded-md transition-colors outline-none text-base py-2 px-3 bg-white border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
                  className="w-full rounded-md transition-colors outline-none text-base py-2 px-3 bg-white border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            <div className="flex justify-end">
              <Button
                variant="primary"
                onClick={handleGenerateList}
                disabled={loading || !startDate || !endDate}
              >
                {loading ? 'Generating...' : 'Generate Grocery List'}
              </Button>
            </div>
          </div>
        </Card>

        {/* Loading state */}
        {loading && (
          <Card variant="default">
            <div className="py-12 flex justify-center">
              <LoadingSpinner />
            </div>
          </Card>
        )}

        {/* Error state */}
        {error && (
          <Card variant="default">
            <div className="p-6 text-center">
              <p className="text-red-500 mb-4">
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
              <div className="flex justify-between items-center mb-6">
                <div>
                  <h2 className="text-lg font-semibold">Your Grocery List</h2>
                  <p className="text-sm text-gray-600">
                    {formatDate(groceryList.start_date)} - {formatDate(groceryList.end_date)}
                  </p>
                  <p className="text-sm text-gray-600">
                    Based on {groceryList.total_meals} planned meal{groceryList.total_meals !== 1 ? 's' : ''}
                  </p>
                </div>
                
                {groceryList.ingredients.length > 0 && (
                  <Button variant="secondary" onClick={handleExportCSV}>
                    Export CSV
                  </Button>
                )}
              </div>

              {groceryList.ingredients.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-500 text-lg">No ingredients found</p>
                  <p className="text-gray-400 text-sm mt-2">
                    Try selecting a different date range or adding recipes to your meal plan.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Ingredient
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Quantity
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Used In
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {groceryList.ingredients.map((ingredient) => (
                        <tr key={ingredient.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm font-medium text-gray-900">
                              {ingredient.name}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm text-gray-900">
                              {formatQuantity(ingredient.quantity_value)} {ingredient.quantity_unit}
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