/**
 * Email validation utility
 * 
 * Validates email addresses using a standard regex pattern.
 * This ensures consistent validation across the application.
 */

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Validates if a string is a valid email address
 * @param email - The email string to validate
 * @returns true if valid email format, false otherwise
 */
export function isValidEmail(email: string): boolean {
  if (!email) {
    return false;
  }
  return EMAIL_REGEX.test(email);
}

/**
 * Validates email and returns an error message if invalid
 * @param email - The email string to validate
 * @returns Error message if invalid, empty string if valid
 */
export function validateEmail(email: string): string {
  if (!email) {
    return 'Email is required';
  }
  if (!EMAIL_REGEX.test(email)) {
    return 'Please enter a valid email address';
  }
  return '';
}
