import { act, renderHook } from '@testing-library/react';
import { describe, expect, test } from 'vitest';
import { useAppStore } from './useAppStore';

describe('useAppStore', () => {
  test('initializes with correct default state', () => {
    const { result } = renderHook(() => useAppStore());

    expect(result.current.currentPage).toBe('home');
    expect(result.current.isMenuOpen).toBe(false);
    expect(result.current.theme).toBe('light');
  });

  test('toggles menu state', () => {
    const { result } = renderHook(() => useAppStore());

    act(() => {
      result.current.toggleMenu();
    });

    expect(result.current.isMenuOpen).toBe(true);
  });

  test('updates current page', () => {
    const { result } = renderHook(() => useAppStore());

    act(() => {
      result.current.setCurrentPage('recipes');
    });

    expect(result.current.currentPage).toBe('recipes');
  });
});
