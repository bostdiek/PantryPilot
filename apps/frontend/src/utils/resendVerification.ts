import { resendVerification } from '../api/endpoints/auth';
import { logger } from '../lib/logger';

/**
 * Handles resending verification email with proper error handling
 *
 * This function:
 * - Calls the resend verification API
 * - Handles errors gracefully (shows success even on failure for enumeration protection)
 * - Always returns success to prevent email enumeration attacks
 *
 * @param email - The email address to send verification to
 * @returns Promise that resolves when operation completes
 */
export async function handleResendVerification(email: string): Promise<void> {
  try {
    await resendVerification(email);
  } catch (err) {
    logger.error('Failed to resend verification email:', err);
    // Don't throw - we show success regardless to prevent enumeration
  }
}
