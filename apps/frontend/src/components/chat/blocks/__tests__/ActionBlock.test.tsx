/**
 * @file ActionBlock.test.tsx
 * Tests for the ActionBlock component with Accept/Cancel functionality.
 */

import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test, vi } from 'vitest';

import type { ActionBlock as ActionBlockType } from '../../../../types/Chat';
import { ActionBlock } from '../ActionBlock';

describe('ActionBlock', () => {
  const defaultBlock: ActionBlockType = {
    type: 'action',
    action_id: 'action-123',
    label: 'Add recipe to meal plan?',
    requires_confirmation: true,
  };

  test('renders action label', () => {
    render(<ActionBlock block={defaultBlock} />);

    expect(screen.getByText('Add recipe to meal plan?')).toBeInTheDocument();
  });

  test('renders Accept and Cancel buttons', () => {
    render(<ActionBlock block={defaultBlock} />);

    expect(screen.getByRole('button', { name: /accept/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });

  test('calls onAccept with action_id when Accept clicked', async () => {
    const user = userEvent.setup();
    const onAccept = vi.fn().mockResolvedValue(undefined);

    render(<ActionBlock block={defaultBlock} onAccept={onAccept} />);

    await user.click(screen.getByRole('button', { name: /accept/i }));

    await waitFor(() => {
      expect(onAccept).toHaveBeenCalledWith('action-123');
    });
  });

  test('calls onCancel with action_id when Cancel clicked', async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn().mockResolvedValue(undefined);

    render(<ActionBlock block={defaultBlock} onCancel={onCancel} />);

    await user.click(screen.getByRole('button', { name: /cancel/i }));

    await waitFor(() => {
      expect(onCancel).toHaveBeenCalledWith('action-123');
    });
  });

  test('shows loading state while accepting', async () => {
    const user = userEvent.setup();
    let resolveAccept: () => void;
    const onAccept = vi.fn().mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          resolveAccept = resolve;
        })
    );

    render(<ActionBlock block={defaultBlock} onAccept={onAccept} />);

    await user.click(screen.getByRole('button', { name: /accept/i }));

    // Should show loading text
    await waitFor(() => {
      expect(screen.getByText(/accepting/i)).toBeInTheDocument();
    });

    // Buttons should be disabled
    expect(screen.getByRole('button', { name: /accepting/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeDisabled();

    // Resolve to clean up
    resolveAccept!();
  });

  test('shows loading state while canceling', async () => {
    const user = userEvent.setup();
    let resolveCancel: () => void;
    const onCancel = vi.fn().mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          resolveCancel = resolve;
        })
    );

    render(<ActionBlock block={defaultBlock} onCancel={onCancel} />);

    await user.click(screen.getByRole('button', { name: /cancel/i }));

    await waitFor(() => {
      expect(screen.getByText(/canceling/i)).toBeInTheDocument();
    });

    // Resolve to clean up
    resolveCancel!();
  });

  test('shows accepted state after successful accept', async () => {
    const user = userEvent.setup();
    const onAccept = vi.fn().mockResolvedValue(undefined);

    render(<ActionBlock block={defaultBlock} onAccept={onAccept} />);

    await user.click(screen.getByRole('button', { name: /accept/i }));

    await waitFor(() => {
      expect(screen.getByText('Action accepted')).toBeInTheDocument();
    });

    // Buttons should be replaced with status
    expect(
      screen.queryByRole('button', { name: /accept/i })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /cancel/i })
    ).not.toBeInTheDocument();
  });

  test('shows canceled state after successful cancel', async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn().mockResolvedValue(undefined);

    render(<ActionBlock block={defaultBlock} onCancel={onCancel} />);

    await user.click(screen.getByRole('button', { name: /cancel/i }));

    await waitFor(() => {
      expect(screen.getByText('Action canceled')).toBeInTheDocument();
    });
  });

  test('reverts to pending on accept error', async () => {
    const user = userEvent.setup();
    const onAccept = vi.fn().mockRejectedValue(new Error('Network error'));

    render(<ActionBlock block={defaultBlock} onAccept={onAccept} />);

    await user.click(screen.getByRole('button', { name: /accept/i }));

    await waitFor(() => {
      // Should return to pending state with buttons visible
      expect(
        screen.getByRole('button', { name: /accept/i })
      ).toBeInTheDocument();
    });
  });

  test('reverts to pending on cancel error', async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn().mockRejectedValue(new Error('Network error'));

    render(<ActionBlock block={defaultBlock} onCancel={onCancel} />);

    await user.click(screen.getByRole('button', { name: /cancel/i }));

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /cancel/i })
      ).toBeInTheDocument();
    });
  });

  test('does nothing when Accept clicked without onAccept handler', async () => {
    const user = userEvent.setup();

    render(<ActionBlock block={defaultBlock} />);

    // Should not throw
    await user.click(screen.getByRole('button', { name: /accept/i }));

    // Buttons should still be visible (no state change)
    expect(screen.getByRole('button', { name: /accept/i })).toBeInTheDocument();
  });

  test('does nothing when Cancel clicked without onCancel handler', async () => {
    const user = userEvent.setup();

    render(<ActionBlock block={defaultBlock} />);

    await user.click(screen.getByRole('button', { name: /cancel/i }));

    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });
});
