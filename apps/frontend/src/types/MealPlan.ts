// Frontend meal planning types aligned with backend schemas

export type DayOfWeek =
  | 'Sunday'
  | 'Monday'
  | 'Tuesday'
  | 'Wednesday'
  | 'Thursday'
  | 'Friday'
  | 'Saturday';

// Single meal entry (planned or cooked)
export interface MealEntry {
  id: string;
  plannedForDate: string; // YYYY-MM-DD
  mealType: 'dinner';
  recipeId?: string;
  isLeftover: boolean;
  isEatingOut: boolean;
  notes?: string;
  orderIndex: number;
  wasCooked: boolean;
  cookedAt?: string; // ISO timestamp
}

// Day plan with entries
export interface DayPlan {
  dayOfWeek: DayOfWeek;
  date: string; // YYYY-MM-DD
  entries: MealEntry[];
}

// Weekly plan starting on Sunday
export interface WeeklyMealPlan {
  weekStartDate: string; // YYYY-MM-DD (Sunday)
  days: DayPlan[];
}

// Input types for creating/updating entries
export interface MealEntryIn {
  plannedForDate: string; // YYYY-MM-DD
  mealType?: 'dinner';
  recipeId?: string;
  isLeftover?: boolean;
  isEatingOut?: boolean;
  notes?: string;
  orderIndex?: number;
}

export type MealEntryPatch = Partial<
  Omit<MealEntryIn, 'plannedForDate'> & {
    plannedForDate: string;
    wasCooked?: boolean;
    cookedAt?: string;
  }
>;
