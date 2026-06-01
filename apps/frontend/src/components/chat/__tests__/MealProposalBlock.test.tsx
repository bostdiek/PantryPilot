import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { MealProposalBlock as MealProposalBlockType } from '../../../types/Chat';

// Mock dependencies
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual =
    await vi.importActual<typeof import('react-router-dom')>(
      'react-router-dom'
    );
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockCreateMealEntry = vi.fn();
vi.mock('../../../api/endpoints/mealPlans', () => ({
  createMealEntry: (...args: unknown[]) => mockCreateMealEntry(...args),
}));

const mockAppendLocalAssistantMessage = vi.fn();
vi.mock('../../../stores/useChatStore', () => ({
  useChatStore: {
    getState: () => ({
      appendLocalAssistantMessage: mockAppendLocalAssistantMessage,
    }),
  },
}));

const mockGetMealProposalStatus = vi.fn();
const mockInvalidateMealProposalStatus = vi.fn();
const mockMarkMealProposalSavedToBook = vi.fn();
const mockMarkMealProposalAddedToPlan = vi.fn();
const mockMarkMealProposalRejected = vi.fn();

vi.mock('../../../utils/mealProposalStatus', () => ({
  getMealProposalInstanceId: () => 'test-proposal-123',
  getMealProposalStatus: (...args: unknown[]) =>
    mockGetMealProposalStatus(...args),
  invalidateMealProposalStatus: (...args: unknown[]) =>
    mockInvalidateMealProposalStatus(...args),
  markMealProposalSavedToBook: (...args: unknown[]) =>
    mockMarkMealProposalSavedToBook(...args),
  markMealProposalAddedToPlan: (...args: unknown[]) =>
    mockMarkMealProposalAddedToPlan(...args),
  markMealProposalRejected: (...args: unknown[]) =>
    mockMarkMealProposalRejected(...args),
}));

import { MealProposalBlock } from '../blocks/MealProposalBlock';

const renderWithRouter = (ui: React.ReactElement) => {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
};

describe('MealProposalBlock', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    mockGetMealProposalStatus.mockReturnValue({
      version: 1,
      phase: 'pending',
      updatedAt: undefined,
      proposalInstanceId: undefined,
      recipeId: undefined,
      returnContext: undefined,
      lastError: undefined,
      savedToBook: false,
      addedToPlan: false,
      rejected: false,
      canRetryAdd: false,
    });
  });

  const baseBlock: MealProposalBlockType = {
    type: 'meal_proposal',
    proposal_id: 'test-proposal-123',
    date: '2026-01-25',
    day_label: 'Saturday',
  };

  describe('rendering', () => {
    it('renders existing recipe proposal correctly', () => {
      const block: MealProposalBlockType = {
        ...baseBlock,
        existing_recipe: {
          id: 'recipe-123',
          title: 'Classic Lasagna',
          image_url: 'https://example.com/lasagna.jpg',
        },
      };

      renderWithRouter(<MealProposalBlock block={block} />);

      expect(screen.getByText('Saturday')).toBeInTheDocument();
      expect(screen.getByText('Classic Lasagna')).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /Accept/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /Reject/i })
      ).toBeInTheDocument();
    });

    it('renders new recipe proposal with Save and Add buttons', () => {
      const block: MealProposalBlockType = {
        ...baseBlock,
        new_recipe: {
          title: 'Beef Bourguignon',
          source_url: 'https://example.com/beef-bourguignon',
          description: 'A classic French beef stew',
        },
      };

      renderWithRouter(<MealProposalBlock block={block} />);

      expect(screen.getByText('Saturday')).toBeInTheDocument();
      expect(screen.getByText('Beef Bourguignon')).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /Save to Recipe Book/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /Add to Meal Plan/i })
      ).toBeInTheDocument();
    });

    it('renders leftover proposal correctly', () => {
      const block: MealProposalBlockType = {
        ...baseBlock,
        is_leftover: true,
        notes: 'Leftovers from Sunday lasagna',
      };

      renderWithRouter(<MealProposalBlock block={block} />);

      expect(screen.getByText('Leftover Day')).toBeInTheDocument();
      expect(
        screen.getByText('Leftovers from Sunday lasagna')
      ).toBeInTheDocument();
    });

    it('renders eating out proposal correctly', () => {
      const block: MealProposalBlockType = {
        ...baseBlock,
        is_eating_out: true,
        notes: 'Pizza night!',
      };

      renderWithRouter(<MealProposalBlock block={block} />);

      expect(screen.getByText('Eating Out')).toBeInTheDocument();
      expect(screen.getByText('Pizza night!')).toBeInTheDocument();
    });
  });

  describe('existing recipe interactions', () => {
    it('accepts existing recipe and creates meal entry', async () => {
      mockCreateMealEntry.mockResolvedValueOnce({ id: 'meal-123' });

      const block: MealProposalBlockType = {
        ...baseBlock,
        existing_recipe: {
          id: 'recipe-123',
          title: 'Classic Lasagna',
        },
      };

      renderWithRouter(<MealProposalBlock block={block} />);

      await userEvent.click(screen.getByRole('button', { name: /Accept/i }));

      await waitFor(() => {
        expect(mockCreateMealEntry).toHaveBeenCalledWith({
          plannedForDate: '2026-01-25',
          mealType: 'dinner',
          recipeId: 'recipe-123',
          isLeftover: false,
          isEatingOut: false,
          notes: undefined,
        });
      });

      expect(screen.getByText(/Added to Saturday/i)).toBeInTheDocument();
    });

    it('shows error when accepting existing recipe fails', async () => {
      mockCreateMealEntry.mockRejectedValueOnce(new Error('Network error'));
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

      const block: MealProposalBlockType = {
        ...baseBlock,
        existing_recipe: {
          id: 'recipe-123',
          title: 'Classic Lasagna',
        },
      };

      renderWithRouter(<MealProposalBlock block={block} />);

      await userEvent.click(screen.getByRole('button', { name: /Accept/i }));

      await waitFor(() => {
        expect(alertSpy).toHaveBeenCalledWith(
          'Failed to add meal to plan. Please try again.'
        );
      });

      alertSpy.mockRestore();
    });
  });

  describe('new recipe interactions', () => {
    it('navigates to recipe creation when Save to Recipe Book is clicked', async () => {
      const block: MealProposalBlockType = {
        ...baseBlock,
        new_recipe: {
          title: 'Beef Bourguignon',
          source_url: 'https://example.com/beef-bourguignon',
        },
      };

      renderWithRouter(<MealProposalBlock block={block} />);

      await userEvent.click(
        screen.getByRole('button', { name: /Save to Recipe Book/i })
      );

      expect(mockNavigate).toHaveBeenCalledWith(
        expect.stringContaining('/recipes/new?')
      );
      expect(mockNavigate).toHaveBeenCalledWith(
        expect.stringContaining(
          'url=https%3A%2F%2Fexample.com%2Fbeef-bourguignon'
        )
      );
      expect(mockNavigate).toHaveBeenCalledWith(
        expect.stringContaining('title=Beef+Bourguignon')
      );
      expect(mockNavigate).toHaveBeenCalledWith(
        expect.stringContaining('mealPlanDate=2026-01-25')
      );
      expect(mockNavigate).toHaveBeenCalledWith(
        expect.stringContaining('returnToAssistant=1')
      );
    });

    it('shows warning when Add to Meal Plan is clicked for unsaved recipe', async () => {
      const block: MealProposalBlockType = {
        ...baseBlock,
        new_recipe: {
          title: 'Beef Bourguignon',
          source_url: 'https://example.com/beef-bourguignon',
        },
      };

      renderWithRouter(<MealProposalBlock block={block} />);

      await userEvent.click(
        screen.getByRole('button', { name: /Add to Meal Plan/i })
      );

      expect(screen.getByText(/Recipe needs to be saved/i)).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /Save to Recipe Book/i })
      ).toBeInTheDocument();
    });
  });

  describe('rejection', () => {
    it('marks proposal as rejected when Reject is clicked', async () => {
      const block: MealProposalBlockType = {
        ...baseBlock,
        existing_recipe: {
          id: 'recipe-123',
          title: 'Classic Lasagna',
        },
      };

      renderWithRouter(<MealProposalBlock block={block} />);

      await userEvent.click(screen.getByRole('button', { name: /Reject/i }));

      expect(screen.getByText(/Rejected/i)).toBeInTheDocument();
    });
  });

  describe('date formatting', () => {
    it('formats ISO date correctly without timezone issues', () => {
      const block: MealProposalBlockType = {
        ...baseBlock,
        date: '2026-01-25',
        existing_recipe: {
          id: 'recipe-123',
          title: 'Classic Lasagna',
        },
      };

      renderWithRouter(<MealProposalBlock block={block} />);

      // Should show "Sat, Jan 25" not the previous day
      expect(screen.getByText(/Jan 25/i)).toBeInTheDocument();
    });
  });

  describe('persisted state recovery', () => {
    it('renders recipe_saved state with continue button', () => {
      mockGetMealProposalStatus.mockReturnValue({
        version: 1,
        phase: 'recipe_saved',
        updatedAt: '2026-01-25T10:00:00Z',
        proposalInstanceId: 'test-proposal-123',
        recipeId: 'recipe-abc',
        returnContext: undefined,
        lastError: undefined,
        savedToBook: true,
        addedToPlan: false,
        rejected: false,
        canRetryAdd: true,
      });

      const block: MealProposalBlockType = {
        ...baseBlock,
        new_recipe: {
          title: 'Beef Bourguignon',
          source_url: 'https://example.com/beef',
        },
      };

      renderWithRouter(<MealProposalBlock block={block} />);

      expect(
        screen.getByText(/Recipe saved to your recipe book/i)
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /Continue to Meal Plan/i })
      ).toBeInTheDocument();
    });

    it('renders retryable_add_failure state with retry button', () => {
      mockGetMealProposalStatus.mockReturnValue({
        version: 1,
        phase: 'retryable_add_failure',
        updatedAt: '2026-01-25T10:00:00Z',
        proposalInstanceId: 'test-proposal-123',
        recipeId: 'recipe-abc',
        returnContext: undefined,
        lastError: 'meal_entry_create_failed',
        savedToBook: true,
        addedToPlan: false,
        rejected: false,
        canRetryAdd: true,
      });

      const block: MealProposalBlockType = {
        ...baseBlock,
        new_recipe: {
          title: 'Beef Bourguignon',
          source_url: 'https://example.com/beef',
        },
      };

      renderWithRouter(<MealProposalBlock block={block} />);

      expect(
        screen.getByText(/Add to meal plan needs one more try/i)
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /Retry Add to Meal Plan/i })
      ).toBeInTheDocument();
    });

    it('renders added_to_plan (accepted) state', () => {
      mockGetMealProposalStatus.mockReturnValue({
        version: 1,
        phase: 'added_to_plan',
        updatedAt: '2026-01-25T10:00:00Z',
        proposalInstanceId: 'test-proposal-123',
        recipeId: 'recipe-abc',
        returnContext: undefined,
        lastError: undefined,
        savedToBook: false,
        addedToPlan: true,
        rejected: false,
        canRetryAdd: false,
      });

      const block: MealProposalBlockType = {
        ...baseBlock,
        existing_recipe: {
          id: 'recipe-123',
          title: 'Classic Lasagna',
        },
      };

      renderWithRouter(<MealProposalBlock block={block} />);

      expect(screen.getByText(/Added to Saturday/i)).toBeInTheDocument();
    });

    it('renders rejected state', () => {
      mockGetMealProposalStatus.mockReturnValue({
        version: 1,
        phase: 'rejected',
        updatedAt: '2026-01-25T10:00:00Z',
        proposalInstanceId: 'test-proposal-123',
        recipeId: undefined,
        returnContext: undefined,
        lastError: undefined,
        savedToBook: false,
        addedToPlan: false,
        rejected: true,
        canRetryAdd: false,
      });

      const block: MealProposalBlockType = {
        ...baseBlock,
        existing_recipe: {
          id: 'recipe-123',
          title: 'Classic Lasagna',
        },
      };

      renderWithRouter(<MealProposalBlock block={block} />);

      expect(screen.getByText(/Rejected/i)).toBeInTheDocument();
    });

    it('calls invalidateMealProposalStatus on mount', () => {
      const block: MealProposalBlockType = {
        ...baseBlock,
        existing_recipe: {
          id: 'recipe-123',
          title: 'Classic Lasagna',
        },
      };

      renderWithRouter(<MealProposalBlock block={block} />);

      expect(mockInvalidateMealProposalStatus).toHaveBeenCalledWith(
        expect.any(String),
        'test-proposal-123'
      );
    });
  });
});
