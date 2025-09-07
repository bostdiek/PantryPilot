// User preferences types for PantryPilot application

export interface UserPreferences {
  // Family and serving preferences
  familySize: number;
  defaultServings: number;
  
  // Dietary restrictions and allergies
  allergies: string[];
  dietaryRestrictions: string[];
  
  // App preferences
  theme: 'light' | 'dark' | 'system';
  units: 'metric' | 'imperial';
  
  // Meal planning preferences
  mealPlanningDays: number; // How many days to plan ahead
  preferredCuisines: string[];
}

export interface UserProfile {
  id: string;
  username: string;
  email: string;
  firstName?: string;
  lastName?: string;
  displayName: string; // Computed from firstName + lastName or username
  isEmailManaged: boolean; // Whether email is managed by external provider
}

export interface UserProfileUpdate {
  firstName?: string;
  lastName?: string;
  username?: string;
}

export interface UserPreferencesStore {
  preferences: UserPreferences;
  isLoaded: boolean;
  
  // Actions
  updatePreferences: (preferences: Partial<UserPreferences>) => void;
  resetPreferences: () => void;
  loadPreferences: () => void;
}

// Default preferences
export const defaultUserPreferences: UserPreferences = {
  familySize: 2,
  defaultServings: 4,
  allergies: [],
  dietaryRestrictions: [],
  theme: 'light',
  units: 'imperial',
  mealPlanningDays: 7,
  preferredCuisines: [],
};

// Common allergy options
export const commonAllergies = [
  'Peanuts',
  'Tree Nuts',
  'Milk/Dairy',
  'Eggs',
  'Fish',
  'Shellfish',
  'Soy',
  'Wheat/Gluten',
  'Sesame',
];

// Common dietary restriction options
export const commonDietaryRestrictions = [
  'Vegetarian',
  'Vegan',
  'Gluten-Free',
  'Dairy-Free',
  'Nut-Free',
  'Low-Carb',
  'Keto',
  'Paleo',
  'Mediterranean',
  'Halal',
  'Kosher',
];

// Common cuisine options
export const commonCuisines = [
  'Italian',
  'Mexican',
  'Chinese',
  'Indian',
  'Thai',
  'Mediterranean',
  'American',
  'French',
  'Japanese',
  'Korean',
  'Middle Eastern',
  'German',
];