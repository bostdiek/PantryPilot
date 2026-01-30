/**
 * Tests for the FeedbackButtons component.
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { FeedbackButtons } from './FeedbackButtons';

// Mock the feedback API
vi.mock('../../api/endpoints/feedback', () => ({
  submitMessageFeedback: vi.fn(),
}));

// Mock the logger
vi.mock('../../lib/logger', () => ({
  logger: {
    error: vi.fn(),
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
  },
}));

import { submitMessageFeedback } from '../../api/endpoints/feedback';

const mockSubmitFeedback = vi.mocked(submitMessageFeedback);

describe('FeedbackButtons', () => {
  const mockMessageId = 'test-message-id-123';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders thumbs up and thumbs down buttons', () => {
    render(<FeedbackButtons messageId={mockMessageId} />);

    expect(
      screen.getByRole('button', { name: /rate response as good/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /rate response as bad/i })
    ).toBeInTheDocument();
  });

  it('calls API when thumbs up is clicked', async () => {
    mockSubmitFeedback.mockResolvedValueOnce({
      status: 'ok',
      message_id: mockMessageId,
      feedback: 'positive',
    });

    render(<FeedbackButtons messageId={mockMessageId} />);

    const thumbsUpButton = screen.getByRole('button', {
      name: /rate response as good/i,
    });
    fireEvent.click(thumbsUpButton);

    await waitFor(() => {
      expect(mockSubmitFeedback).toHaveBeenCalledWith(
        mockMessageId,
        'positive'
      );
    });
  });

  it('calls API when thumbs down is clicked', async () => {
    mockSubmitFeedback.mockResolvedValueOnce({
      status: 'ok',
      message_id: mockMessageId,
      feedback: 'negative',
    });

    render(<FeedbackButtons messageId={mockMessageId} />);

    const thumbsDownButton = screen.getByRole('button', {
      name: /rate response as bad/i,
    });
    fireEvent.click(thumbsDownButton);

    await waitFor(() => {
      expect(mockSubmitFeedback).toHaveBeenCalledWith(
        mockMessageId,
        'negative'
      );
    });
  });

  it('disables buttons after feedback is submitted', async () => {
    mockSubmitFeedback.mockResolvedValueOnce({
      status: 'ok',
      message_id: mockMessageId,
      feedback: 'positive',
    });

    render(<FeedbackButtons messageId={mockMessageId} />);

    const thumbsUpButton = screen.getByRole('button', {
      name: /rate response as good/i,
    });
    const thumbsDownButton = screen.getByRole('button', {
      name: /rate response as bad/i,
    });

    fireEvent.click(thumbsUpButton);

    await waitFor(() => {
      expect(thumbsUpButton).toBeDisabled();
      expect(thumbsDownButton).toBeDisabled();
    });
  });

  it('shows initial feedback state when provided', () => {
    render(
      <FeedbackButtons messageId={mockMessageId} initialFeedback="positive" />
    );

    const thumbsUpButton = screen.getByRole('button', {
      name: /rate response as good/i,
    });
    const thumbsDownButton = screen.getByRole('button', {
      name: /rate response as bad/i,
    });

    // Both should be disabled when initial feedback is set
    expect(thumbsUpButton).toBeDisabled();
    expect(thumbsDownButton).toBeDisabled();
    // Thumbs up should have the selected style (aria-pressed)
    expect(thumbsUpButton).toHaveAttribute('aria-pressed', 'true');
  });

  it('calls onFeedbackSubmitted callback after successful submission', async () => {
    mockSubmitFeedback.mockResolvedValueOnce({
      status: 'ok',
      message_id: mockMessageId,
      feedback: 'negative',
    });

    const onFeedbackSubmitted = vi.fn();
    render(
      <FeedbackButtons
        messageId={mockMessageId}
        onFeedbackSubmitted={onFeedbackSubmitted}
      />
    );

    const thumbsDownButton = screen.getByRole('button', {
      name: /rate response as bad/i,
    });
    fireEvent.click(thumbsDownButton);

    await waitFor(() => {
      expect(onFeedbackSubmitted).toHaveBeenCalledWith(
        mockMessageId,
        'negative'
      );
    });
  });

  it('handles API errors gracefully without breaking UI', async () => {
    mockSubmitFeedback.mockRejectedValueOnce(new Error('Network error'));

    render(<FeedbackButtons messageId={mockMessageId} />);

    const thumbsUpButton = screen.getByRole('button', {
      name: /rate response as good/i,
    });
    fireEvent.click(thumbsUpButton);

    // After error, buttons should still be enabled (not submitted)
    await waitFor(() => {
      expect(thumbsUpButton).not.toBeDisabled();
    });
  });

  it('prevents multiple submissions while one is in progress', async () => {
    // Create a promise that we can resolve manually
    let resolvePromise: (value: unknown) => void;
    const pendingPromise = new Promise((resolve) => {
      resolvePromise = resolve;
    });
    mockSubmitFeedback.mockReturnValueOnce(pendingPromise as Promise<never>);

    render(<FeedbackButtons messageId={mockMessageId} />);

    const thumbsUpButton = screen.getByRole('button', {
      name: /rate response as good/i,
    });
    const thumbsDownButton = screen.getByRole('button', {
      name: /rate response as bad/i,
    });

    // Click thumbs up
    fireEvent.click(thumbsUpButton);

    // Try clicking thumbs down while first request is pending
    fireEvent.click(thumbsDownButton);

    // Should only have one API call
    expect(mockSubmitFeedback).toHaveBeenCalledTimes(1);

    // Resolve the pending promise
    resolvePromise!({
      status: 'ok',
      message_id: mockMessageId,
      feedback: 'positive',
    });
  });
});
