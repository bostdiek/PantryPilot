/**
 * Date utility functions that use the user's local timezone.
 * These functions ensure dates are displayed and compared based on the user's browser timezone,
 * not UTC.
 */

/**
 * Formats a Date object to YYYY-MM-DD string in local timezone.
 * @param date - The date to format
 * @returns Date string in YYYY-MM-DD format
 */
export function toLocalYyyyMmDd(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * Gets the start of the week (Sunday) for a given date in local timezone.
 * @param date - The date to find the week start for
 * @returns Date object representing the Sunday of that week at 00:00:00 local time
 */
export function getLocalStartOfSundayWeek(date: Date): Date {
  const day = new Date(date);
  const dayOfWeek = day.getDay(); // 0 (Sunday) to 6 (Saturday)
  const start = new Date(
    day.getFullYear(),
    day.getMonth(),
    day.getDate() - dayOfWeek
  );
  return start;
}

/**
 * Adds a number of days to a YYYY-MM-DD date string in local timezone.
 * @param yyyyMmDd - Date string in YYYY-MM-DD format
 * @param days - Number of days to add (can be negative)
 * @returns New date string in YYYY-MM-DD format
 */
export function addDaysToDateString(yyyyMmDd: string, days: number): string {
  const [year, month, day] = yyyyMmDd.split('-').map(Number);
  const date = new Date(year, month - 1, day);
  date.setDate(date.getDate() + days);
  return toLocalYyyyMmDd(date);
}
