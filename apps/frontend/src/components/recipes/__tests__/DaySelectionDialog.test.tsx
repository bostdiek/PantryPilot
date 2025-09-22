import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { dayButtonAriaLabel } from '../../../utils/labelHelpers';
import { DaySelectionDialog } from '../DaySelectionDialog';

const mockDays = [
  { dayOfWeek: 'Monday', date: '2025-01-13', isToday: false },
  { dayOfWeek: 'Tuesday', date: '2025-01-14', isToday: true },
  { dayOfWeek: 'Wednesday', date: '2025-01-15', isToday: false },
  { dayOfWeek: 'Thursday', date: '2025-01-16', isToday: false },
  { dayOfWeek: 'Friday', date: '2025-01-17', isToday: false },
  { dayOfWeek: 'Saturday', date: '2025-01-18', isToday: false },
  { dayOfWeek: 'Sunday', date: '2025-01-19', isToday: false },
];

describe('DaySelectionDialog', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onDaySelect: vi.fn(),
    recipeTitle: 'Spaghetti Carbonara',
    availableDays: mockDays,
  };

  it('renders the dialog with recipe title', () => {
    render(<DaySelectionDialog {...defaultProps} />);

    expect(screen.getByText('Add Recipe to Day')).toBeInTheDocument();
    expect(screen.getByText(/Select which day to add/)).toBeInTheDocument();
    expect(screen.getByText('Spaghetti Carbonara')).toBeInTheDocument();
  });

  it('renders all available days', () => {
    render(<DaySelectionDialog {...defaultProps} />);

    mockDays.forEach((day) => {
      expect(screen.getByText(day.dayOfWeek)).toBeInTheDocument();
      expect(screen.getByText(day.date, { exact: false })).toBeInTheDocument();
    });
  });

  it('highlights today with primary variant', () => {
    render(<DaySelectionDialog {...defaultProps} />);

    const tuesdayButton = screen.getByTestId('day-button-tuesday');
    expect(tuesdayButton).toBeInTheDocument();
    expect(tuesdayButton).toHaveAttribute('data-variant', 'primary');
    expect(tuesdayButton).toHaveAttribute(
      'aria-label',
      dayButtonAriaLabel('Tuesday', '2025-01-14', true)
    );
  });

  it('calls onDaySelect when a day is clicked', async () => {
    const onDaySelect = vi.fn();
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <DaySelectionDialog
        {...defaultProps}
        onDaySelect={onDaySelect}
        onClose={onClose}
      />
    );

    const mondayButton = screen.getByRole('button', { name: /Monday/ });
    await user.click(mondayButton);

    expect(onDaySelect).toHaveBeenCalledWith('Monday', '2025-01-13');
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose when dialog backdrop is clicked', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(<DaySelectionDialog {...defaultProps} onClose={onClose} />);

    // Click on the backdrop (overlay) to close dialog
    const overlay = screen.getByRole('dialog');
    await user.click(overlay);

    expect(onClose).toHaveBeenCalled();
  });

  it('does not render when isOpen is false', () => {
    render(<DaySelectionDialog {...defaultProps} isOpen={false} />);

    expect(screen.queryByText('Add Recipe to Day')).not.toBeInTheDocument();
  });

  it('handles empty availableDays array', () => {
    render(<DaySelectionDialog {...defaultProps} availableDays={[]} />);

    expect(screen.getByText('Add Recipe to Day')).toBeInTheDocument();
    expect(screen.getByText(/Select which day to add/)).toBeInTheDocument();

    // Should not have any day buttons
    mockDays.forEach((day) => {
      expect(screen.queryByText(day.dayOfWeek)).not.toBeInTheDocument();
    });
  });

  it('supports keyboard navigation', async () => {
    const onDaySelect = vi.fn();
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <DaySelectionDialog
        {...defaultProps}
        onDaySelect={onDaySelect}
        onClose={onClose}
      />
    );

    // Tab to first day button and press Enter
    await user.tab();
    await user.keyboard('{Enter}');

    expect(onDaySelect).toHaveBeenCalledWith('Monday', '2025-01-13');
    expect(onClose).toHaveBeenCalled();
  });

  it('closes dialog when Escape key is pressed', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(<DaySelectionDialog {...defaultProps} onClose={onClose} />);

    // Press Escape key
    await user.keyboard('{Escape}');

    expect(onClose).toHaveBeenCalled();
  });

  it('has proper ARIA attributes for accessibility', () => {
    render(<DaySelectionDialog {...defaultProps} />);

    // Check for dialog role
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    // Check for group role on days container
    expect(
      screen.getByRole('group', { name: 'Days of the week' })
    ).toBeInTheDocument();

    // Check that each day button has proper aria-label
    mockDays.forEach((day) => {
      const expectedLabel = dayButtonAriaLabel(
        day.dayOfWeek,
        day.date,
        !!day.isToday
      );
      expect(
        screen.getByRole('button', { name: expectedLabel })
      ).toBeInTheDocument();
    });
  });
});
