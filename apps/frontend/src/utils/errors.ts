export function getErrorMessage(
  error: unknown,
  fallback = 'Unexpected error'
): string {
  if (error instanceof Error && error.message) return error.message;
  if (typeof error === 'string') return error;
  if (
    error &&
    typeof error === 'object' &&
    'message' in error &&
    typeof (error as { message?: unknown }).message === 'string'
  ) {
    return (error as { message: string }).message;
  }
  return fallback;
}
