import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import RecipesDetail from '../RecipesDetail';
import { useRecipeStore } from '../../stores/useRecipeStore';
import type { Recipe } from '../../types/Recipe';

// Mock the router hooks
const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ id: 'test-recipe-id' }),
    useLoaderData: () => mockRecipe,
  };
});

// Mock the recipe store
vi.mock('../../stores/useRecipeStore');

const mockRecipe: Recipe = {
  id: 'test-recipe-id',
  title: 'Test Recipe',
  description: 'A delicious test recipe',
  ingredients: [
    {
      id: 'ing-1',
      name: 'Test Ingredient 1',
      quantity_value: 2,
      quantity_unit: 'cups',
      prep: { method: 'chopped' },
      is_optional: false,
    },
    {
      id: 'ing-2',
      name: 'Test Ingredient 2',
      quantity_value: 1,
      quantity_unit: 'tbsp',
      prep: {},
      is_optional: true,
    },
  ],
  instructions: ['First step', 'Second step', 'Third step'],
  prep_time_minutes: 15,
  cook_time_minutes: 30,
  total_time_minutes: 45,
  serving_min: 4,
  serving_max: 6,
  difficulty: 'medium',
  category: 'dinner',
  ethnicity: 'Italian',
  oven_temperature_f: 350,
  user_notes: 'This is a great recipe for family dinners',
  link_source: '',
  ai_summary: '',
  created_at: new Date('2024-01-01'),
  updated_at: new Date('2024-01-01'),
};

const mockDeleteRecipe = vi.fn();
const mockDuplicateRecipe = vi.fn();

describe('RecipesDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Setup default mock store state
    vi.mocked(useRecipeStore).mockReturnValue({
      deleteRecipe: mockDeleteRecipe,
      duplicateRecipe: mockDuplicateRecipe,
      isLoading: false,
      recipes: [mockRecipe],
      filteredRecipes: [mockRecipe],
      error: null,
      filters: {
        query: '',
        categories: [],
        difficulties: [],
        cookTimeMin: 0,
        cookTimeMax: 999,
        includedIngredients: [],
        excludedIngredients: [],
      },
      sortBy: 'relevance',
      pagination: { page: 1, pageSize: 20, total: 1 },
      fetchRecipes: vi.fn(),
      fetchRecipeById: vi.fn(),
      addRecipe: vi.fn(),
      updateRecipe: vi.fn(),
      setFilters: vi.fn(),
      setSortBy: vi.fn(),
      setPage: vi.fn(),
      clearFilters: vi.fn(),
      applyFiltersAndSort: vi.fn(),
    });
  });

  const renderRecipesDetail = () => {
    return render(
      <MemoryRouter>
        <RecipesDetail />
      </MemoryRouter>
    );
  };

  it('renders recipe details correctly', () => {
    renderRecipesDetail();

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Test Recipe');
    expect(screen.getByText('A delicious test recipe')).toBeInTheDocument();
    
    // Check metadata
    expect(screen.getByText('15')).toBeInTheDocument(); // prep time
    expect(screen.getByText('30')).toBeInTheDocument(); // cook time
    expect(screen.getByText('45')).toBeInTheDocument(); // total time
    expect(screen.getByText('4-6')).toBeInTheDocument(); // servings
  });

  it('displays ingredients with proper formatting', () => {
    renderRecipesDetail();

    expect(screen.getByText(/2 cups/)).toBeInTheDocument();
    expect(screen.getByText(/Test Ingredient 1/)).toBeInTheDocument();
    expect(screen.getByText(/chopped/)).toBeInTheDocument();
    expect(screen.getByText(/1 tbsp/)).toBeInTheDocument();
    expect(screen.getByText(/Test Ingredient 2/)).toBeInTheDocument();
    expect(screen.getByText(/(optional)/)).toBeInTheDocument();
  });

  it('displays instructions in numbered order', () => {
    renderRecipesDetail();

    expect(screen.getByText('First step')).toBeInTheDocument();
    expect(screen.getByText('Second step')).toBeInTheDocument();
    expect(screen.getByText('Third step')).toBeInTheDocument();
  });

  it('displays tags correctly', () => {
    renderRecipesDetail();

    expect(screen.getByText('dinner')).toBeInTheDocument();
    expect(screen.getByText('medium')).toBeInTheDocument();
    expect(screen.getByText('Italian')).toBeInTheDocument();
    expect(screen.getByText('350°F')).toBeInTheDocument();
  });

  it('displays user notes when present', () => {
    renderRecipesDetail();

    expect(screen.getByText('This is a great recipe for family dinners')).toBeInTheDocument();
  });

  it('renders action buttons', () => {
    renderRecipesDetail();

    expect(screen.getByRole('button', { name: /edit test recipe/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /duplicate test recipe/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /delete test recipe/i })).toBeInTheDocument();
  });

  it('navigates to edit page when edit button is clicked', async () => {
    const user = userEvent.setup();
    renderRecipesDetail();

    const editButton = screen.getByRole('button', { name: /edit test recipe/i });
    await user.click(editButton);

    expect(mockNavigate).toHaveBeenCalledWith('/recipes/test-recipe-id/edit');
  });

  it('calls duplicate recipe when duplicate button is clicked', async () => {
    const user = userEvent.setup();
    mockDuplicateRecipe.mockResolvedValue({ ...mockRecipe, id: 'new-recipe-id' });
    renderRecipesDetail();

    const duplicateButton = screen.getByRole('button', { name: /duplicate test recipe/i });
    await user.click(duplicateButton);

    expect(mockDuplicateRecipe).toHaveBeenCalledWith('test-recipe-id');
    
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/recipes/new-recipe-id', { replace: true });
    });
  });

  it('shows loading state when duplicating', async () => {
    const user = userEvent.setup();
    mockDuplicateRecipe.mockImplementation(() => new Promise(() => {})); // Never resolves
    renderRecipesDetail();

    const duplicateButton = screen.getByRole('button', { name: /duplicate test recipe/i });
    await user.click(duplicateButton);

    expect(duplicateButton).toBeDisabled();
  });

  it('opens delete confirmation modal when delete button is clicked', async () => {
    const user = userEvent.setup();
    renderRecipesDetail();

    const deleteButton = screen.getByRole('button', { name: /delete test recipe/i });
    await user.click(deleteButton);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /delete recipe/i })).toBeInTheDocument();
    expect(screen.getByText((content, element) => {
      return element ? element.textContent?.includes('Are you sure you want to delete "Test Recipe"') ?? false : false;
    })).toBeInTheDocument();
  });

  it('closes delete modal when cancel is clicked', async () => {
    const user = userEvent.setup();
    renderRecipesDetail();

    // Open modal
    const deleteButton = screen.getByRole('button', { name: /delete test recipe/i });
    await user.click(deleteButton);

    // Close modal
    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  it('deletes recipe and navigates when confirmed', async () => {
    const user = userEvent.setup();
    mockDeleteRecipe.mockResolvedValue(true);
    renderRecipesDetail();

    // Open modal
    const deleteButton = screen.getByRole('button', { name: /delete test recipe/i });
    await user.click(deleteButton);

    // Confirm deletion
    const confirmButton = screen.getByRole('button', { name: /delete recipe/i });
    await user.click(confirmButton);

    expect(mockDeleteRecipe).toHaveBeenCalledWith('test-recipe-id');
    
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/recipes', { replace: true });
    });
  });

  it('has proper semantic structure and accessibility', () => {
    renderRecipesDetail();

    // Check for proper headings
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: /ingredients/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: /instructions/i })).toBeInTheDocument();

    // Check for proper landmarks
    expect(screen.getByRole('article')).toBeInTheDocument();
    
    // Check for lists
    expect(screen.getAllByRole('list')).toHaveLength(2); // ingredients and instructions

    // Check aria-labels on buttons
    expect(screen.getByRole('button', { name: /edit test recipe/i })).toHaveAttribute('aria-label');
    expect(screen.getByRole('button', { name: /duplicate test recipe/i })).toHaveAttribute('aria-label');
    expect(screen.getByRole('button', { name: /delete test recipe/i })).toHaveAttribute('aria-label');
  });
});