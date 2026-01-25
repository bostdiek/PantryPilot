import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { Recipe } from '../../../types/Recipe';
import {
  DuplicateRecipeModal,
  type DuplicateRecipeModalProps,
  type SimilarRecipeMatch,
} from '../DuplicateRecipeModal';

// Mock react-router-dom navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock matchMedia for Dialog component
beforeEach(() => {
  mockNavigate.mockClear();

  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query) => ({
      matches: false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
});

// Test data
const mockExistingRecipe: Recipe = {
  id: 'existing-123',
  title: 'Spaghetti Carbonara',
  description: 'A classic Italian pasta dish',
  category: 'dinner',
  difficulty: 'medium',
  ethnicity: 'Italian',
  prep_time_minutes: 15,
  cook_time_minutes: 20,
  total_time_minutes: 35,
  serving_min: 4,
  serving_max: 6,
  oven_temperature_f: null,
  ingredients: [],
  instructions: [],
  user_notes: null,
  created_at: new Date('2024-01-01'),
  updated_at: new Date('2024-01-01'),
};

const mockSimilarRecipes: SimilarRecipeMatch[] = [
  {
    recipe: {
      ...mockExistingRecipe,
      id: 'similar-1',
      title: 'Pasta Carbonara',
    },
    similarity: 0.85,
  },
  {
    recipe: {
      ...mockExistingRecipe,
      id: 'similar-2',
      title: 'Carbonara Style Pasta',
    },
    similarity: 0.72,
  },
];

const defaultProps: DuplicateRecipeModalProps = {
  isOpen: true,
  onClose: vi.fn(),
  duplicateType: 'exact',
  existingRecipe: mockExistingRecipe,
  onViewExisting: vi.fn(),
  onCreateAnyway: vi.fn(),
};

const renderModal = (props: Partial<DuplicateRecipeModalProps> = {}) => {
  return render(
    <MemoryRouter>
      <DuplicateRecipeModal {...defaultProps} {...props} />
    </MemoryRouter>
  );
};

describe('DuplicateRecipeModal', () => {
  describe('Exact Match Display', () => {
    it('renders with exact match title', () => {
      renderModal({ duplicateType: 'exact' });

      expect(screen.getByText('Recipe Already Exists')).toBeInTheDocument();
    });

    it('shows existing recipe details for exact match', () => {
      renderModal({ duplicateType: 'exact' });

      expect(screen.getByText('Spaghetti Carbonara')).toBeInTheDocument();
      expect(
        screen.getByText('A classic Italian pasta dish')
      ).toBeInTheDocument();
    });

    it('shows View Existing button for exact match', () => {
      renderModal({ duplicateType: 'exact' });

      expect(
        screen.getByRole('button', { name: /view existing/i })
      ).toBeInTheDocument();
    });

    it('shows recipe metadata (time, difficulty)', () => {
      renderModal({ duplicateType: 'exact' });

      expect(screen.getByText('35 min')).toBeInTheDocument();
      expect(screen.getByText('medium')).toBeInTheDocument();
    });
  });

  describe('Similar Match Display', () => {
    it('renders with similar matches title', () => {
      renderModal({
        duplicateType: 'similar',
        existingRecipe: undefined,
        similarRecipes: mockSimilarRecipes,
      });

      expect(screen.getByText('Similar Recipes Found')).toBeInTheDocument();
    });

    it('shows all similar recipes', () => {
      renderModal({
        duplicateType: 'similar',
        existingRecipe: undefined,
        similarRecipes: mockSimilarRecipes,
      });

      expect(screen.getByText('Pasta Carbonara')).toBeInTheDocument();
      expect(screen.getByText('Carbonara Style Pasta')).toBeInTheDocument();
    });

    it('shows similarity percentages', () => {
      renderModal({
        duplicateType: 'similar',
        existingRecipe: undefined,
        similarRecipes: mockSimilarRecipes,
      });

      expect(screen.getByText('85% match')).toBeInTheDocument();
      expect(screen.getByText('72% match')).toBeInTheDocument();
    });

    it('shows informational text for similar matches', () => {
      renderModal({
        duplicateType: 'similar',
        existingRecipe: undefined,
        similarRecipes: mockSimilarRecipes,
      });

      expect(
        screen.getByText(/we found similar recipes in your collection/i)
      ).toBeInTheDocument();
    });
  });

  describe('User Actions', () => {
    it('calls onClose when Cancel is clicked', async () => {
      const onClose = vi.fn();
      const user = userEvent.setup();

      renderModal({ onClose });

      await user.click(screen.getByRole('button', { name: /cancel/i }));

      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('calls onCreateAnyway when Create Anyway is clicked', async () => {
      const onCreateAnyway = vi.fn();
      const user = userEvent.setup();

      renderModal({ onCreateAnyway });

      await user.click(screen.getByRole('button', { name: /create anyway/i }));

      expect(onCreateAnyway).toHaveBeenCalledTimes(1);
    });

    it('calls onViewExisting and navigates for exact match', async () => {
      const onViewExisting = vi.fn();
      const onClose = vi.fn();
      const user = userEvent.setup();

      renderModal({ onViewExisting, onClose });

      await user.click(screen.getByRole('button', { name: /view existing/i }));

      expect(onViewExisting).toHaveBeenCalledWith('existing-123');
      expect(mockNavigate).toHaveBeenCalledWith('/recipes/existing-123');
      expect(onClose).toHaveBeenCalled();
    });

    it('allows selecting a similar recipe before viewing', async () => {
      const onViewExisting = vi.fn();
      const user = userEvent.setup();

      renderModal({
        duplicateType: 'similar',
        existingRecipe: undefined,
        similarRecipes: mockSimilarRecipes,
        onViewExisting,
      });

      // Click on a similar recipe to select it
      await user.click(screen.getByText('Carbonara Style Pasta'));

      // Should show "View Selected" button
      await user.click(screen.getByRole('button', { name: /view selected/i }));

      expect(onViewExisting).toHaveBeenCalledWith('similar-2');
    });
  });

  describe('Loading State', () => {
    it('disables buttons when isCreatingAnyway is true', () => {
      renderModal({ isCreatingAnyway: true });

      expect(screen.getByRole('button', { name: /cancel/i })).toBeDisabled();
      expect(
        screen.getByRole('button', { name: /create anyway/i })
      ).toBeDisabled();
      expect(
        screen.getByRole('button', { name: /view existing/i })
      ).toBeDisabled();
    });

    it('shows loading state on Create Anyway button', () => {
      renderModal({ isCreatingAnyway: true });

      const createButton = screen.getByRole('button', {
        name: /create anyway/i,
      });
      expect(createButton).toBeDisabled();
    });

    it('prevents closing modal when loading', async () => {
      const onClose = vi.fn();
      const user = userEvent.setup();

      renderModal({ isCreatingAnyway: true, onClose });

      await user.click(screen.getByRole('button', { name: /cancel/i }));

      // onClose should not be called when loading
      expect(onClose).not.toHaveBeenCalled();
    });
  });

  describe('Modal State', () => {
    it('does not render when isOpen is false', () => {
      renderModal({ isOpen: false });

      expect(
        screen.queryByText('Recipe Already Exists')
      ).not.toBeInTheDocument();
    });

    it('renders when isOpen is true', () => {
      renderModal({ isOpen: true });

      expect(screen.getByText('Recipe Already Exists')).toBeInTheDocument();
    });
  });

  describe('Recipe Preview Card', () => {
    it('shows category badge when category is present', () => {
      renderModal();

      expect(screen.getByText('dinner')).toBeInTheDocument();
    });

    it('highlights selected recipe', async () => {
      const user = userEvent.setup();

      renderModal({
        duplicateType: 'similar',
        existingRecipe: undefined,
        similarRecipes: mockSimilarRecipes,
      });

      // Click to select first recipe
      const firstRecipe = screen.getByText('Pasta Carbonara').closest('button');
      await user.click(firstRecipe!);

      // Should have selection styling (ring/border)
      expect(firstRecipe).toHaveClass('border-green-500');
    });
  });
});
