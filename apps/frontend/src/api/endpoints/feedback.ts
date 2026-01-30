/**
 * API endpoints for user feedback on AI assistant responses.
 */

import { useAuthStore } from '../../stores/useAuthStore';
import { getApiBaseUrl } from '../client';

/**
 * Feedback types for training data quality signals.
 */
export type FeedbackValue = 'positive' | 'negative';

/**
 * Response from feedback submission endpoint.
 */
export interface SubmitFeedbackResponse {
  status: string;
  message_id: string;
  feedback: FeedbackValue;
}

/**
 * Gets auth headers for API requests.
 */
function getAuthHeaders(): Record<string, string> {
  const token = useAuthStore.getState().token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Submit user feedback (👍/👎) for an assistant message.
 *
 * @param messageId - The message ID to submit feedback for
 * @param feedback - The feedback value ('positive' or 'negative')
 * @returns The API response confirming feedback submission
 * @throws Error if the API request fails
 */
export async function submitMessageFeedback(
  messageId: string,
  feedback: FeedbackValue
): Promise<SubmitFeedbackResponse> {
  const API_BASE_URL = getApiBaseUrl();
  const url = `${API_BASE_URL}/api/v1/messages/${messageId}/feedback`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ user_feedback: feedback }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const errorJson = JSON.parse(errorText);
      errorDetail = errorJson.detail || errorDetail;
    } catch {
      // Use default error detail
    }
    throw new Error(errorDetail);
  }

  return response.json();
}
