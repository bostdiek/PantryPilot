import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore, useDisplayName } from '../useAuthStore';

describe('useAuthStore', () => {
  beforeEach(() => {
    // Reset the store before each test
    act(() => {
      useAuthStore.setState({
        token: null,
        user: null,
        hasHydrated: false,
      });
    });
  });

  it('should initialize with null token and user', () => {
    const { result } = renderHook(() => useAuthStore());

    expect(result.current.token).toBeNull();
    expect(result.current.user).toBeNull();
    expect(result.current.hasHydrated).toBe(false);
  });

  it('should set token', () => {
    const { result } = renderHook(() => useAuthStore());

    act(() => {
      result.current.setToken('test-token');
    });

    expect(result.current.token).toBe('test-token');
  });

  it('should set user', () => {
    const { result } = renderHook(() => useAuthStore());
    const testUser = {
      id: '123',
      username: 'testuser',
      email: 'test@example.com',
      first_name: 'John',
      last_name: 'Doe',
    };

    act(() => {
      result.current.setUser(testUser);
    });

    expect(result.current.user).toEqual(testUser);
  });

  it('should login with token and user', () => {
    const { result } = renderHook(() => useAuthStore());
    const testUser = {
      id: '123',
      username: 'testuser',
      email: 'test@example.com',
      first_name: 'John',
      last_name: 'Doe',
    };

    act(() => {
      result.current.login('test-token', testUser);
    });

    expect(result.current.token).toBe('test-token');
    expect(result.current.user).toEqual(testUser);
  });

  it('should logout and clear token and user', () => {
    const { result } = renderHook(() => useAuthStore());
    const testUser = {
      id: '123',
      username: 'testuser',
      email: 'test@example.com',
    };

    // First login
    act(() => {
      result.current.login('test-token', testUser);
    });

    expect(result.current.token).toBe('test-token');
    expect(result.current.user).toEqual(testUser);

    // Then logout
    act(() => {
      result.current.logout();
    });

    expect(result.current.token).toBeNull();
    expect(result.current.user).toBeNull();
  });

  describe('getDisplayName', () => {
    it('should return "Guest" when no user is set', () => {
      const { result } = renderHook(() => useAuthStore());

      expect(result.current.getDisplayName()).toBe('Guest');
    });

    it('should return username when no first/last name', () => {
      const { result } = renderHook(() => useAuthStore());
      const testUser = {
        id: '123',
        username: 'testuser',
        email: 'test@example.com',
      };

      act(() => {
        result.current.setUser(testUser);
      });

      expect(result.current.getDisplayName()).toBe('testuser');
    });

    it('should return full name when both first and last name exist', () => {
      const { result } = renderHook(() => useAuthStore());
      const testUser = {
        id: '123',
        username: 'testuser',
        email: 'test@example.com',
        first_name: 'John',
        last_name: 'Doe',
      };

      act(() => {
        result.current.setUser(testUser);
      });

      expect(result.current.getDisplayName()).toBe('John Doe');
    });

    it('should return first name only when last name is empty', () => {
      const { result } = renderHook(() => useAuthStore());
      const testUser = {
        id: '123',
        username: 'testuser',
        email: 'test@example.com',
        first_name: 'John',
        last_name: '',
      };

      act(() => {
        result.current.setUser(testUser);
      });

      expect(result.current.getDisplayName()).toBe('John');
    });

    it('should return last name only when first name is empty', () => {
      const { result } = renderHook(() => useAuthStore());
      const testUser = {
        id: '123',
        username: 'testuser',
        email: 'test@example.com',
        first_name: '',
        last_name: 'Doe',
      };

      act(() => {
        result.current.setUser(testUser);
      });

      expect(result.current.getDisplayName()).toBe('Doe');
    });

    it('should handle undefined first/last names', () => {
      const { result } = renderHook(() => useAuthStore());
      const testUser = {
        id: '123',
        username: 'testuser',
        email: 'test@example.com',
        first_name: undefined,
        last_name: undefined,
      };

      act(() => {
        result.current.setUser(testUser);
      });

      expect(result.current.getDisplayName()).toBe('testuser');
    });
  });
});

describe('useDisplayName hook', () => {
  beforeEach(() => {
    // Reset the store before each test
    act(() => {
      useAuthStore.setState({
        token: null,
        user: null,
        hasHydrated: false,
      });
    });
  });

  it('should return Guest when no user', () => {
    const { result } = renderHook(() => useDisplayName());

    expect(result.current).toBe('Guest');
  });

  it('should return display name when user exists', () => {
    const testUser = {
      id: '123',
      username: 'testuser',
      email: 'test@example.com',
      first_name: 'John',
      last_name: 'Doe',
    };

    act(() => {
      useAuthStore.getState().setUser(testUser);
    });

    const { result } = renderHook(() => useDisplayName());

    expect(result.current).toBe('John Doe');
  });
});