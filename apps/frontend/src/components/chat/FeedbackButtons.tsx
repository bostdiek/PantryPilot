/**
 * Feedback buttons component for AI assistant messages.
 *
 * Allows users to rate assistant responses with 👍/👎 for training data quality signals.
 */

import { Check, ThumbsDown, ThumbsUp, X } from 'lucide-react';
import { useEffect, useState } from 'react';

import {
  submitMessageFeedback,
  type FeedbackValue,
} from '../../api/endpoints/feedback';
import { logger } from '../../lib/logger';

/** Brief flash duration for success/error indicator */
const FEEDBACK_INDICATOR_MS = 1500;

interface FeedbackButtonsProps {
  /** The message ID to submit feedback for */
  messageId: string;
  /** Initial feedback value if already submitted */
  initialFeedback?: FeedbackValue | null;
  /** Callback when feedback is successfully submitted */
  onFeedbackSubmitted?: (messageId: string, feedback: FeedbackValue) => void;
}

/**
 * Renders thumbs up/down buttons for assistant message feedback.
 *
 * - Only one button can be selected at a time
 * - Buttons are disabled after feedback is submitted
 * - Shows loading state during API call
 * - Handles errors gracefully
 */
export function FeedbackButtons({
  messageId,
  initialFeedback = null,
  onFeedbackSubmitted,
}: FeedbackButtonsProps) {
  const [feedback, setFeedback] = useState<FeedbackValue | null>(
    initialFeedback
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<
    'idle' | 'success' | 'error'
  >('idle');

  // Clear status indicator after brief display
  useEffect(() => {
    if (submitStatus !== 'idle') {
      const timer = setTimeout(
        () => setSubmitStatus('idle'),
        FEEDBACK_INDICATOR_MS
      );
      return () => clearTimeout(timer);
    }
  }, [submitStatus]);

  const handleFeedback = async (value: FeedbackValue) => {
    if (feedback !== null || isSubmitting) {
      return; // Already submitted or in progress
    }

    setIsSubmitting(true);
    setSubmitStatus('idle');
    try {
      await submitMessageFeedback(messageId, value);
      setFeedback(value);
      setSubmitStatus('success');
      onFeedbackSubmitted?.(messageId, value);
    } catch (error) {
      logger.error('Failed to submit feedback:', error);
      setSubmitStatus('error');
      // Don't set feedback - allow retry
    } finally {
      setIsSubmitting(false);
    }
  };

  const isDisabled = feedback !== null || isSubmitting;

  // Show status indicator briefly after submission attempt
  if (submitStatus === 'success') {
    return (
      <div
        className="flex items-center gap-1 text-green-600"
        aria-live="polite"
      >
        <Check size={14} aria-label="Feedback submitted" />
      </div>
    );
  }

  if (submitStatus === 'error') {
    return (
      <div className="flex items-center gap-1 text-red-500" aria-live="polite">
        <X size={14} aria-label="Feedback failed" />
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1">
      <button
        type="button"
        onClick={() => handleFeedback('positive')}
        disabled={isDisabled}
        className={`rounded p-1 transition-colors ${
          feedback === 'positive'
            ? 'text-green-600'
            : 'text-gray-400 hover:bg-gray-200 hover:text-gray-600 disabled:hover:bg-transparent disabled:hover:text-gray-400'
        } disabled:cursor-default disabled:opacity-50`}
        title="Good response"
        aria-label="Rate response as good"
        aria-pressed={feedback === 'positive'}
      >
        <ThumbsUp size={14} />
      </button>
      <button
        type="button"
        onClick={() => handleFeedback('negative')}
        disabled={isDisabled}
        className={`rounded p-1 transition-colors ${
          feedback === 'negative'
            ? 'text-red-600'
            : 'text-gray-400 hover:bg-gray-200 hover:text-gray-600 disabled:hover:bg-transparent disabled:hover:text-gray-400'
        } disabled:cursor-default disabled:opacity-50`}
        title="Bad response"
        aria-label="Rate response as bad"
        aria-pressed={feedback === 'negative'}
      >
        <ThumbsDown size={14} />
      </button>
    </div>
  );
}
