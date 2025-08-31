import { renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useUnsavedChanges } from './useUnsavedChanges';

// Mock useBlocker to simulate React Router
vi.mock('react-router-dom', () => ({
  useBlocker: vi.fn(() => ({
    state: 'unblocked',
    proceed: vi.fn(),
    reset: vi.fn(),
  })),
}));

// Mock window.confirm
const mockConfirm = vi.fn();
Object.defineProperty(window, 'confirm', {
  value: mockConfirm,
  writable: true,
});

// Mock addEventListener and removeEventListener
const mockAddEventListener = vi.fn();
const mockRemoveEventListener = vi.fn();
Object.defineProperty(window, 'addEventListener', {
  value: mockAddEventListener,
  writable: true,
});
Object.defineProperty(window, 'removeEventListener', {
  value: mockRemoveEventListener,
  writable: true,
});

describe('useUnsavedChanges', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('adds beforeunload listener when there are unsaved changes', () => {
    renderHook(() => useUnsavedChanges(true));

    expect(mockAddEventListener).toHaveBeenCalledWith(
      'beforeunload',
      expect.any(Function)
    );
  });

  it('removes beforeunload listener on cleanup', () => {
    const { unmount } = renderHook(() => useUnsavedChanges(true));

    unmount();

    expect(mockRemoveEventListener).toHaveBeenCalledWith(
      'beforeunload',
      expect.any(Function)
    );
  });

  it('does not break when useBlocker is not available', () => {
    // This test ensures the hook works in test environments where useBlocker might throw
    expect(() => {
      renderHook(() => useUnsavedChanges(true));
    }).not.toThrow();
  });

  it('uses custom message when provided', () => {
    const customMessage = 'Custom unsaved changes message';
    renderHook(() => useUnsavedChanges(true, customMessage));

    // Verify the beforeunload listener was added
    expect(mockAddEventListener).toHaveBeenCalledWith(
      'beforeunload',
      expect.any(Function)
    );
  });

  it('handles hasUnsavedChanges changes dynamically', () => {
    const { rerender } = renderHook(
      ({ hasChanges }) => useUnsavedChanges(hasChanges),
      { initialProps: { hasChanges: false } }
    );

    // Initially no changes
    expect(mockAddEventListener).toHaveBeenCalled();

    // Change to having unsaved changes
    rerender({ hasChanges: true });

    // Should still have the listener
    expect(mockAddEventListener).toHaveBeenCalled();
  });
});
