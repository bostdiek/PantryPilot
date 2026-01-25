import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { AddMealDialog } from '../AddMealDialog';

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('AddMealDialog', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    targetDate: '2025-01-13',
    dayOfWeek: 'Monday',
    onAddLeftover: vi.fn(),
    onAddEatingOut: vi.fn(),
  };

  beforeEach(() => {
    mockNavigate.mockClear();
  });

  it('renders the dialog with day of week', () => {
    render(
      <MemoryRouter>
        <AddMealDialog {...defaultProps} />
      </MemoryRouter>
    );

    expect(screen.getByText('Add to Monday')).toBeInTheDocument();
  });

  it('renders all three meal option buttons', () => {
    render(
      <MemoryRouter>
        <AddMealDialog {...defaultProps} />
      </MemoryRouter>
    );

    expect(
      screen.getByRole('button', { name: /add recipe/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /leftovers/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /eating out/i })
    ).toBeInTheDocument();
  });

  it('navigates to recipes page when Add Recipe is clicked', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <AddMealDialog {...defaultProps} onClose={onClose} />
      </MemoryRouter>
    );

    const recipeButton = screen.getByRole('button', { name: /add recipe/i });
    await user.click(recipeButton);

    expect(mockNavigate).toHaveBeenCalledWith(
      '/recipes?addToDate=2025-01-13&dayLabel=Monday'
    );
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onAddLeftover and closes when Leftovers is clicked', async () => {
    const onAddLeftover = vi.fn();
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <AddMealDialog
          {...defaultProps}
          onAddLeftover={onAddLeftover}
          onClose={onClose}
        />
      </MemoryRouter>
    );

    const leftoverButton = screen.getByRole('button', { name: /leftovers/i });
    await user.click(leftoverButton);

    expect(onAddLeftover).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onAddEatingOut and closes when Eating Out is clicked', async () => {
    const onAddEatingOut = vi.fn();
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <AddMealDialog
          {...defaultProps}
          onAddEatingOut={onAddEatingOut}
          onClose={onClose}
        />
      </MemoryRouter>
    );

    const eatingOutButton = screen.getByRole('button', {
      name: /eating out/i,
    });
    await user.click(eatingOutButton);

    expect(onAddEatingOut).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it('closes dialog when Cancel button clicked', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <AddMealDialog {...defaultProps} onClose={onClose} />
      </MemoryRouter>
    );

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    expect(onClose).toHaveBeenCalled();
  });

  it('closes dialog when Escape key is pressed', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <AddMealDialog {...defaultProps} onClose={onClose} />
      </MemoryRouter>
    );

    await user.keyboard('{Escape}');

    expect(onClose).toHaveBeenCalled();
  });

  it('does not render when isOpen is false', () => {
    render(
      <MemoryRouter>
        <AddMealDialog {...defaultProps} isOpen={false} />
      </MemoryRouter>
    );

    expect(screen.queryByText('Add to Monday')).not.toBeInTheDocument();
  });

  it('has proper accessibility attributes', () => {
    render(
      <MemoryRouter>
        <AddMealDialog {...defaultProps} />
      </MemoryRouter>
    );

    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('encodes day label in navigation URL', async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <AddMealDialog
          {...defaultProps}
          dayOfWeek="Friday"
          targetDate="2025-01-17"
        />
      </MemoryRouter>
    );

    const recipeButton = screen.getByRole('button', { name: /add recipe/i });
    await user.click(recipeButton);

    expect(mockNavigate).toHaveBeenCalledWith(
      '/recipes?addToDate=2025-01-17&dayLabel=Friday'
    );
  });
});
