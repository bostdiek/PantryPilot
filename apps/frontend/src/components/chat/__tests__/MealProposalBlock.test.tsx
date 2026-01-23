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

vi.mock('../../../utils/mealProposalStatus', () => ({
  getMealProposalStatus: () => ({
    savedToBook: false,
    addedToPlan: false,
    rejected: false,
  }),
  markMealProposalSavedToBook: vi.fn(),
  markMealProposalAddedToPlan: vi.fn(),
  markMealProposalRejected: vi.fn(),
}));

import { MealProposalBlock } from '../blocks/MealProposalBlock';

const renderWithRouter = (ui: React.ReactElement) => {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
};

describe('MealProposalBlock', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
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
});
