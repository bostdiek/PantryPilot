import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { useUserPreferencesStore } from '../useUserPreferencesStore';
import { defaultUserPreferences } from '../../types/UserPreferences';

describe('useUserPreferencesStore', () => {
  beforeEach(() => {
    // Reset the store before each test
    act(() => {
      useUserPreferencesStore.setState({
        preferences: defaultUserPreferences,
        isLoaded: false,
      });
    });
  });

  it('should initialize with default preferences', () => {
    const { result } = renderHook(() => useUserPreferencesStore());

    expect(result.current.preferences).toEqual(defaultUserPreferences);
    expect(result.current.isLoaded).toBe(false);
  });

  it('should update preferences', () => {
    const { result } = renderHook(() => useUserPreferencesStore());

    act(() => {
      result.current.updatePreferences({
        familySize: 5,
        theme: 'dark',
      });
    });

    expect(result.current.preferences.familySize).toBe(5);
    expect(result.current.preferences.theme).toBe('dark');
    // Other preferences should remain unchanged
    expect(result.current.preferences.defaultServings).toBe(defaultUserPreferences.defaultServings);
  });

  it('should reset preferences to defaults', () => {
    const { result } = renderHook(() => useUserPreferencesStore());

    // First modify preferences
    act(() => {
      result.current.updatePreferences({
        familySize: 10,
        allergies: ['Nuts', 'Dairy'],
        theme: 'dark',
      });
    });

    // Verify they were changed
    expect(result.current.preferences.familySize).toBe(10);
    expect(result.current.preferences.allergies).toEqual(['Nuts', 'Dairy']);
    expect(result.current.preferences.theme).toBe('dark');

    // Reset preferences
    act(() => {
      result.current.resetPreferences();
    });

    // Verify they are back to defaults
    expect(result.current.preferences).toEqual(defaultUserPreferences);
  });

  it('should mark as loaded', () => {
    const { result } = renderHook(() => useUserPreferencesStore());

    expect(result.current.isLoaded).toBe(false);

    act(() => {
      result.current.loadPreferences();
    });

    expect(result.current.isLoaded).toBe(true);
  });

  it('should update individual preference fields correctly', () => {
    const { result } = renderHook(() => useUserPreferencesStore());

    // Update allergies
    act(() => {
      result.current.updatePreferences({
        allergies: ['Peanuts', 'Shellfish'],
      });
    });

    expect(result.current.preferences.allergies).toEqual(['Peanuts', 'Shellfish']);

    // Update dietary restrictions
    act(() => {
      result.current.updatePreferences({
        dietaryRestrictions: ['Vegan', 'Gluten-Free'],
      });
    });

    expect(result.current.preferences.dietaryRestrictions).toEqual(['Vegan', 'Gluten-Free']);
    // Allergies should remain unchanged
    expect(result.current.preferences.allergies).toEqual(['Peanuts', 'Shellfish']);

    // Update preferred cuisines
    act(() => {
      result.current.updatePreferences({
        preferredCuisines: ['Italian', 'Mexican', 'Thai'],
      });
    });

    expect(result.current.preferences.preferredCuisines).toEqual(['Italian', 'Mexican', 'Thai']);
  });

  it('should update numeric preferences correctly', () => {
    const { result } = renderHook(() => useUserPreferencesStore());

    act(() => {
      result.current.updatePreferences({
        familySize: 6,
        defaultServings: 8,
        mealPlanningDays: 14,
      });
    });

    expect(result.current.preferences.familySize).toBe(6);
    expect(result.current.preferences.defaultServings).toBe(8);
    expect(result.current.preferences.mealPlanningDays).toBe(14);
  });

  it('should handle partial updates without affecting other fields', () => {
    const { result } = renderHook(() => useUserPreferencesStore());

    // Set initial state with multiple fields
    act(() => {
      result.current.updatePreferences({
        familySize: 3,
        allergies: ['Nuts'],
        theme: 'dark',
        units: 'metric',
      });
    });

    // Update only one field
    act(() => {
      result.current.updatePreferences({
        familySize: 4,
      });
    });

    // Only familySize should change
    expect(result.current.preferences.familySize).toBe(4);
    expect(result.current.preferences.allergies).toEqual(['Nuts']);
    expect(result.current.preferences.theme).toBe('dark');
    expect(result.current.preferences.units).toBe('metric');
  });
});