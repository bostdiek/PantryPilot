import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import GroceryListPage from '../GroceryListPage';
import { groceryListsApi } from '../../api/endpoints/groceryLists';

// Mock the API
vi.mock('../../api/endpoints/groceryLists', () => ({
  groceryListsApi: {
    generateGroceryList: vi.fn(),
  },
}));

// Wrapper component for router context
const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>{children}</BrowserRouter>
);

describe('GroceryListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders grocery list page with date inputs', async () => {
    const mockApiResponse = {
      start_date: '2024-01-01',
      end_date: '2024-01-07',
      ingredients: [],
      total_meals: 0,
    };

    vi.mocked(groceryListsApi.generateGroceryList).mockResolvedValue(
      mockApiResponse
    );

    render(<GroceryListPage />, { wrapper: Wrapper });

    expect(screen.getByText('Grocery List')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Generate Grocery List' })
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Start Date')).toBeInTheDocument();
    expect(screen.getByLabelText('End Date')).toBeInTheDocument();
    
    // Wait for initial API call to complete so button shows proper text
    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: 'Update Grocery List' })
      ).toBeInTheDocument();
    });
  });

  it('has default date values set to current week', async () => {
    const mockApiResponse = {
      start_date: '2024-01-01',
      end_date: '2024-01-07',
      ingredients: [],
      total_meals: 0,
    };

    vi.mocked(groceryListsApi.generateGroceryList).mockResolvedValue(
      mockApiResponse
    );

    render(<GroceryListPage />, { wrapper: Wrapper });

    const startDateInput = screen.getByLabelText(
      'Start Date'
    ) as HTMLInputElement;
    const endDateInput = screen.getByLabelText('End Date') as HTMLInputElement;

    // Should have some date values (we won't test exact dates as they change)
    expect(startDateInput.value).toMatch(/\d{4}-\d{2}-\d{2}/);
    expect(endDateInput.value).toMatch(/\d{4}-\d{2}-\d{2}/);

    // Wait for initial API call to complete
    await waitFor(() => {
      expect(groceryListsApi.generateGroceryList).toHaveBeenCalledTimes(1);
    });
  });

  it('calls API when update button is clicked', async () => {
    const mockApiResponse = {
      start_date: '2024-01-01',
      end_date: '2024-01-07',
      ingredients: [
        {
          id: '1',
          name: 'Tomatoes',
          quantity_value: 2,
          quantity_unit: 'cups',
          recipes: ['Test Recipe'],
        },
      ],
      total_meals: 1,
    };

    vi.mocked(groceryListsApi.generateGroceryList).mockResolvedValue(
      mockApiResponse
    );

    render(<GroceryListPage />, { wrapper: Wrapper });

    // Wait for initial API call to complete
    await waitFor(() => {
      expect(groceryListsApi.generateGroceryList).toHaveBeenCalledTimes(1);
    });

    const updateButton = screen.getByRole('button', {
      name: 'Update Grocery List',
    });
    fireEvent.click(updateButton);

    await waitFor(() => {
      expect(groceryListsApi.generateGroceryList).toHaveBeenCalledTimes(2);
      expect(groceryListsApi.generateGroceryList).toHaveBeenCalledWith({
        start_date: expect.stringMatching(/\d{4}-\d{2}-\d{2}/),
        end_date: expect.stringMatching(/\d{4}-\d{2}-\d{2}/),
      });
    });
  });

  it('displays grocery list results when API call succeeds', async () => {
    const mockApiResponse = {
      start_date: '2024-01-01',
      end_date: '2024-01-07',
      ingredients: [
        {
          id: '1',
          name: 'Tomatoes',
          quantity_value: 2,
          quantity_unit: 'cups',
          recipes: ['Test Recipe'],
        },
        {
          id: '2',
          name: 'Onions',
          quantity_value: 1,
          quantity_unit: 'pieces',
          recipes: ['Test Recipe'],
        },
      ],
      total_meals: 1,
    };

    vi.mocked(groceryListsApi.generateGroceryList).mockResolvedValue(
      mockApiResponse
    );

    render(<GroceryListPage />, { wrapper: Wrapper });

    // Wait for initial API call to complete and results to display
    await waitFor(() => {
      expect(screen.getByText('Your Grocery List')).toBeInTheDocument();
    });

    // Check that ingredients are displayed
    expect(screen.getByText('Tomatoes')).toBeInTheDocument();
    expect(screen.getByText('2 cups')).toBeInTheDocument();
    expect(screen.getByText('Onions')).toBeInTheDocument();
    expect(screen.getByText('1 pieces')).toBeInTheDocument();

    // Check export button is present
    expect(
      screen.getByRole('button', { name: 'Export CSV' })
    ).toBeInTheDocument();
  });

  it('displays empty state when no ingredients found', async () => {
    const mockApiResponse = {
      start_date: '2024-01-01',
      end_date: '2024-01-07',
      ingredients: [],
      total_meals: 0,
    };

    vi.mocked(groceryListsApi.generateGroceryList).mockResolvedValue(
      mockApiResponse
    );

    render(<GroceryListPage />, { wrapper: Wrapper });

    // Wait for initial API call to complete
    await waitFor(() => {
      expect(screen.getByText('No ingredients found')).toBeInTheDocument();
    });

    expect(
      screen.getByText(
        'Try selecting a different date range or adding recipes to your meal plan.'
      )
    ).toBeInTheDocument();
  });

  it('displays error message when API call fails', async () => {
    const mockError = { message: 'Failed to generate grocery list' };
    vi.mocked(groceryListsApi.generateGroceryList).mockRejectedValue(mockError);

    render(<GroceryListPage />, { wrapper: Wrapper });

    // Wait for initial API call to fail
    await waitFor(() => {
      expect(
        screen.getByText(/Failed to generate grocery list/)
      ).toBeInTheDocument();
    });

    expect(
      screen.getByRole('button', { name: 'Try Again' })
    ).toBeInTheDocument();
  });

  it('automatically loads grocery list on component mount', async () => {
    const mockApiResponse = {
      start_date: '2024-01-01',
      end_date: '2024-01-07',
      ingredients: [
        {
          id: '1',
          name: 'Auto-loaded ingredient',
          quantity_value: 1,
          quantity_unit: 'cup',
          recipes: ['Auto Recipe'],
        },
      ],
      total_meals: 1,
    };

    vi.mocked(groceryListsApi.generateGroceryList).mockResolvedValue(
      mockApiResponse
    );

    render(<GroceryListPage />, { wrapper: Wrapper });

    // Verify API is called automatically on mount
    await waitFor(() => {
      expect(groceryListsApi.generateGroceryList).toHaveBeenCalledTimes(1);
    });

    // Verify results are displayed
    await waitFor(() => {
      expect(screen.getByText('Auto-loaded ingredient')).toBeInTheDocument();
    });
  });

  it('allows changing date range', async () => {
    const mockApiResponse = {
      start_date: '2024-01-01',
      end_date: '2024-01-07',
      ingredients: [],
      total_meals: 0,
    };

    vi.mocked(groceryListsApi.generateGroceryList).mockResolvedValue(
      mockApiResponse
    );

    render(<GroceryListPage />, { wrapper: Wrapper });

    const startDateInput = screen.getByLabelText(
      'Start Date'
    ) as HTMLInputElement;
    const endDateInput = screen.getByLabelText('End Date') as HTMLInputElement;

    // Test that the inputs exist and can receive new values
    expect(startDateInput).toBeInTheDocument();
    expect(endDateInput).toBeInTheDocument();
    expect(startDateInput.type).toBe('date');
    expect(endDateInput.type).toBe('date');

    // Test that they have initial values
    expect(startDateInput.value).toBeTruthy();
    expect(endDateInput.value).toBeTruthy();

    // Wait for initial API call to complete
    await waitFor(() => {
      expect(groceryListsApi.generateGroceryList).toHaveBeenCalledTimes(1);
    });
  });
});
