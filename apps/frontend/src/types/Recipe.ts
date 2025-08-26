import type { Ingredient } from './Ingredients';

/**
 * Recipe category options
 */
export const RECIPE_CATEGORIES = [
  'breakfast',
  'lunch',
  'dinner',
  'dessert',
  'snack',
  'appetizer',
] as const;
export type RecipeCategory = (typeof RECIPE_CATEGORIES)[number];

/**
 * Recipe difficulty options
 */
export const RECIPE_DIFFICULTIES = ['easy', 'medium', 'hard'] as const;
export type RecipeDifficulty = (typeof RECIPE_DIFFICULTIES)[number];

/**
 * Recipe domain type
 */
export type Recipe = {
  id: string;
  title: string;
  description?: string;
  ingredients: Ingredient[];
  instructions: string[];
  prep_time_minutes: number;
  cook_time_minutes: number;
  serving_min: number;
  serving_max?: number;
  difficulty: RecipeDifficulty;
  category: RecipeCategory;
  ethnicity?: string;
  oven_temperature_f?: number;
  user_notes?: string;
  link_source?: string;
  total_time_minutes: number;
  ai_summary?: string;
  created_at: Date;
  updated_at: Date;
};

/**
 * Recipe creation type
 */
export type RecipeCreate = {
  title: string;
  description?: string;
  ingredients: Omit<Ingredient, 'id'>[];
  instructions: string[];
  prep_time_minutes: number;
  cook_time_minutes: number;
  serving_min: number;
  serving_max?: number;
  difficulty: RecipeDifficulty;
  category: RecipeCategory;
  ethnicity?: string;
  oven_temperature_f?: number;
  user_notes?: string;
  link_source?: string;
};
