import type { Ingredient } from './Ingredients';

type Recipe = {
  id: string;
  title: string;
  description: string;
  ingredients: Ingredient[];
  instructions: string[];
  cookTime: number; // in minutes
  prepTime: number; // in minutes
  servings: number;
  difficulty: 'easy' | 'medium' | 'hard';
  tags: string[];
  imageUrl?: string; // optional
  ovenTemperatureF?: number; //optional
  createdAt: Date;
  updatedAt: Date;
};

export type { Recipe };
