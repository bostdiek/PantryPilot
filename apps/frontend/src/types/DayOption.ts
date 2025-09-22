/**
 * Day option for day selection in meal planning
 */
export interface DayOption {
  /** The day of the week (e.g., "Monday", "Tuesday") */
  dayOfWeek: string;
  /** The date in YYYY-MM-DD format */
  date: string;
  /** Whether this day is today */
  isToday?: boolean;
}
