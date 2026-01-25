// User preferences types for Smart Meal Planner application

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

  // Location preferences (for weather and meal planning)
  city?: string;
  stateOrRegion?: string;
  postalCode?: string;
  country?: string;
}

// Backend API types (snake_case to match backend)
export interface UserPreferencesResponse {
  id: string;
  user_id: string;
  family_size: number;
  default_servings: number;
  allergies: string[];
  dietary_restrictions: string[];
  theme: 'light' | 'dark' | 'system';
  units: 'metric' | 'imperial';
  meal_planning_days: number;
  preferred_cuisines: string[];
  city?: string;
  state_or_region?: string;
  postal_code?: string;
  country?: string;
}

export interface UserPreferencesUpdate {
  family_size?: number;
  default_servings?: number;
  allergies?: string[];
  dietary_restrictions?: string[];
  theme?: 'light' | 'dark' | 'system';
  units?: 'metric' | 'imperial';
  meal_planning_days?: number;
  preferred_cuisines?: string[];
  city?: string;
  state_or_region?: string;
  postal_code?: string;
  country?: string;
}

export interface UserProfileResponse {
  id: string;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  preferences?: UserPreferencesResponse;
}

export interface UserProfileUpdate {
  first_name?: string;
  last_name?: string;
  username?: string;
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

export interface UserPreferencesStore {
  preferences: UserPreferences;
  isLoaded: boolean;

  // Actions
  updatePreferences: (preferences: Partial<UserPreferences>) => void;
  resetPreferences: () => void;
  loadPreferences: () => void;
  syncWithBackend: (backendPrefs: UserPreferencesResponse) => void;
}

// Conversion helpers
export function toFrontendPreferences(
  backendPrefs: UserPreferencesResponse
): UserPreferences {
  return {
    familySize: backendPrefs.family_size,
    defaultServings: backendPrefs.default_servings,
    allergies: backendPrefs.allergies,
    dietaryRestrictions: backendPrefs.dietary_restrictions,
    theme: backendPrefs.theme,
    units: backendPrefs.units,
    mealPlanningDays: backendPrefs.meal_planning_days,
    preferredCuisines: backendPrefs.preferred_cuisines,
    city: backendPrefs.city,
    stateOrRegion: backendPrefs.state_or_region,
    postalCode: backendPrefs.postal_code,
    country: backendPrefs.country,
  };
}

export function toBackendPreferences(
  frontendPrefs: Partial<UserPreferences>
): UserPreferencesUpdate {
  const update: UserPreferencesUpdate = {};

  if (frontendPrefs.familySize !== undefined) {
    update.family_size = frontendPrefs.familySize;
  }
  if (frontendPrefs.defaultServings !== undefined) {
    update.default_servings = frontendPrefs.defaultServings;
  }
  if (frontendPrefs.allergies !== undefined) {
    update.allergies = frontendPrefs.allergies;
  }
  if (frontendPrefs.dietaryRestrictions !== undefined) {
    update.dietary_restrictions = frontendPrefs.dietaryRestrictions;
  }
  if (frontendPrefs.theme !== undefined) {
    update.theme = frontendPrefs.theme;
  }
  if (frontendPrefs.units !== undefined) {
    update.units = frontendPrefs.units;
  }
  if (frontendPrefs.mealPlanningDays !== undefined) {
    update.meal_planning_days = frontendPrefs.mealPlanningDays;
  }
  if (frontendPrefs.preferredCuisines !== undefined) {
    update.preferred_cuisines = frontendPrefs.preferredCuisines;
  }
  if (frontendPrefs.city !== undefined) {
    update.city = frontendPrefs.city;
  }
  if (frontendPrefs.stateOrRegion !== undefined) {
    update.state_or_region = frontendPrefs.stateOrRegion;
  }
  if (frontendPrefs.postalCode !== undefined) {
    update.postal_code = frontendPrefs.postalCode;
  }
  if (frontendPrefs.country !== undefined) {
    update.country = frontendPrefs.country;
  }

  return update;
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
  city: undefined,
  stateOrRegion: undefined,
  postalCode: undefined,
  country: 'US',
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
