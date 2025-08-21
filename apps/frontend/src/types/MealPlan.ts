type Meal = {
  dayOfWeek:
    | 'Sunday'
    | 'Monday'
    | 'Tuesday'
    | 'Wednesday'
    | 'Thursday'
    | 'Friday'
    | 'Saturday';
  recipeId?: string;
  isLeftover: boolean;
  isEatingOut: boolean;
  notes?: string;
};

type MealPlan = {
  meals: Meal[];
};

export type { Meal, MealPlan };
