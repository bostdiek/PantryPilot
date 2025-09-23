import { renderHook } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useSwipeGesture } from '../useSwipeGesture';

describe('useSwipeGesture', () => {
  let onSwipeDown: ReturnType<typeof vi.fn>;
  let onSwipeUp: ReturnType<typeof vi.fn>;
  let onSwipeLeft: ReturnType<typeof vi.fn>;
  let onSwipeRight: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.useFakeTimers();
    onSwipeDown = vi.fn();
    onSwipeUp = vi.fn();
    onSwipeLeft = vi.fn();
    onSwipeRight = vi.fn();
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it('should return a ref object', () => {
    const { result } = renderHook(() =>
      useSwipeGesture({
        onSwipeDown,
        threshold: 50,
        velocity: 0.1,
      })
    );

    expect(result.current).toHaveProperty('current');
    expect(result.current.current).toBeNull(); // Initially null
  });

  it('should handle configuration options', () => {
    const { result } = renderHook(() =>
      useSwipeGesture({
        onSwipeDown,
        onSwipeUp,
        onSwipeLeft,
        onSwipeRight,
        threshold: 100,
        velocity: 0.5,
      })
    );

    // Should not throw and should return a ref
    expect(result.current).toBeDefined();
  });
});
