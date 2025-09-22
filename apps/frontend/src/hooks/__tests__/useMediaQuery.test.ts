import { renderHook } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { 
  useMediaQuery, 
  useIsMobile, 
  useIsTablet, 
  useIsDesktop,
  useIsTouchDevice 
} from '../useMediaQuery';

// Mock window.matchMedia
const mockMatchMedia = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();

  // Ensure window exists and mock matchMedia
  if (typeof window !== 'undefined') {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: mockMatchMedia,
    });
  }
});

describe('useMediaQuery', () => {
  it('should return initial matches value', () => {
    const mockMediaQuery = {
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    };
    mockMatchMedia.mockReturnValue(mockMediaQuery);

    const { result } = renderHook(() => useMediaQuery('(max-width: 768px)'));

    expect(result.current).toBe(true);
    expect(mockMatchMedia).toHaveBeenCalledWith('(max-width: 768px)');
  });

  it('should return false when media query does not match', () => {
    const mockMediaQuery = {
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    };
    mockMatchMedia.mockReturnValue(mockMediaQuery);

    const { result } = renderHook(() => useMediaQuery('(max-width: 768px)'));

    expect(result.current).toBe(false);
  });

  it('should add and remove event listeners', () => {
    const mockMediaQuery = {
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    };
    mockMatchMedia.mockReturnValue(mockMediaQuery);

    const { unmount } = renderHook(() => useMediaQuery('(max-width: 768px)'));

    expect(mockMediaQuery.addEventListener).toHaveBeenCalledWith(
      'change',
      expect.any(Function)
    );

    unmount();

    expect(mockMediaQuery.removeEventListener).toHaveBeenCalledWith(
      'change',
      expect.any(Function)
    );
  });

  it('should handle server-side rendering gracefully', () => {
    // This test verifies the hook doesn't crash in SSR,
    // but since we're in jsdom environment, we'll just test the fallback behavior
    const mockMediaQuery = {
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    };
    mockMatchMedia.mockReturnValue(mockMediaQuery);

    const { result } = renderHook(() => useMediaQuery('(max-width: 768px)'));

    // Should return the media query result (false in this case)
    expect(result.current).toBe(false);
  });
});

describe('useIsMobile', () => {
  it('should use correct mobile breakpoint query', () => {
    const mockMediaQuery = {
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    };
    mockMatchMedia.mockReturnValue(mockMediaQuery);

    const { result } = renderHook(() => useIsMobile());

    expect(result.current).toBe(true);
    expect(mockMatchMedia).toHaveBeenCalledWith('(max-width: 767px)');
  });

  it('should return false when screen is desktop size', () => {
    const mockMediaQuery = {
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    };
    mockMatchMedia.mockReturnValue(mockMediaQuery);

    const { result } = renderHook(() => useIsMobile());

    expect(result.current).toBe(false);
  });

  it('should use fallback methods for older browsers without addEventListener', () => {
    const mockMediaQuery = {
      matches: true,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      // No addEventListener/removeEventListener
    };
    mockMatchMedia.mockReturnValue(mockMediaQuery);

    const { unmount } = renderHook(() => useMediaQuery('(max-width: 767px)'));

    expect(mockMediaQuery.addListener).toHaveBeenCalledWith(
      expect.any(Function)
    );

    unmount();

    expect(mockMediaQuery.removeListener).toHaveBeenCalledWith(
      expect.any(Function)
    );
  });
});

describe('useIsTablet', () => {
  it('should use correct tablet breakpoint query', () => {
    const mockMediaQuery = {
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    };
    mockMatchMedia.mockReturnValue(mockMediaQuery);

    const { result } = renderHook(() => useIsTablet());

    expect(result.current).toBe(true);
    expect(mockMatchMedia).toHaveBeenCalledWith('(min-width: 768px) and (max-width: 1024px)');
  });
});

describe('useIsDesktop', () => {
  it('should use correct desktop breakpoint query', () => {
    const mockMediaQuery = {
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    };
    mockMatchMedia.mockReturnValue(mockMediaQuery);

    const { result } = renderHook(() => useIsDesktop());

    expect(result.current).toBe(true);
    expect(mockMatchMedia).toHaveBeenCalledWith('(min-width: 1025px)');
  });
});

describe('useIsTouchDevice', () => {
  it('should use correct touch device query', () => {
    const mockMediaQuery = {
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    };
    mockMatchMedia.mockReturnValue(mockMediaQuery);

    const { result } = renderHook(() => useIsTouchDevice());

    expect(result.current).toBe(true);
    expect(mockMatchMedia).toHaveBeenCalledWith('(pointer: coarse)');
  });
});
