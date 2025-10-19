import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AddByPhotoModal } from '../AddByPhotoModal';

// Mock navigation
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

// Basic mocks for stores and utilities used by the component
let isAuthenticated = true;
vi.mock('../../../stores/useAuthStore', () => ({
  useIsAuthenticated: () => isAuthenticated,
  useAuthStore: { getState: () => ({ token: isAuthenticated ? 'tok' : null }) },
}));
vi.mock('../../../stores/useRecipeStore', () => ({
  useRecipeStore: { getState: () => ({ setFormFromSuggestion: vi.fn() }) },
}));
vi.mock('../../../hooks/useMediaQuery', () => ({ useIsMobile: () => false }));
vi.mock('../../../lib/logger', () => ({
  logger: { debug: vi.fn(), warn: vi.fn(), error: vi.fn() },
}));
vi.mock('../../../utils/generateImageThumbnail', () => ({
  generateImageThumbnail: vi.fn().mockResolvedValue(null),
}));

const mockExtractStream = vi.fn();
vi.mock('../../../api/endpoints/aiDrafts', () => ({
  extractRecipeFromImageStream: (...args: any[]) => mockExtractStream(...args),
  extractRecipeFromImage: () =>
    Promise.resolve({ signed_url: '/recipes/new?ai=1&draftId=fallback' }),
  isSafeInternalPath: (u: string) => {
    try {
      const a = new URL(u, window.location.origin);
      return (
        a.origin === window.location.origin && a.pathname.startsWith('/recipes')
      );
    } catch {
      return false;
    }
  },
}));

describe('AddByPhotoModal (focused)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = '';
    // ensure default authenticated state for each test
    isAuthenticated = true;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows validation error for non-image files', async () => {
    const onClose = vi.fn();
    render(<AddByPhotoModal isOpen={true} onClose={onClose} />);

    const input = document.querySelector(
      'input[type=file]'
    ) as HTMLInputElement;
    const bad = new File(['x'], 'bad.txt', { type: 'text/plain' });
    fireEvent.change(input, { target: { files: [bad] } });

    await waitFor(() =>
      expect(screen.getByText(/Please select only image files/)).toBeTruthy()
    );
  });

  it('redirects to login when not authenticated', async () => {
    // simulate unauthenticated by toggling the mocked value
    // the module mock above reads `isAuthenticated` variable, so set it false
    // instead of trying to re-require the module which fails in this env
    // (avoid runtime require in tests)
    isAuthenticated = false;
    const onClose = vi.fn();
    render(<AddByPhotoModal isOpen={true} onClose={onClose} />);

    const input = document.querySelector(
      'input[type=file]'
    ) as HTMLInputElement;
    const img = new File(['i'], 'i.jpg', { type: 'image/jpeg' });
    fireEvent.change(input, { target: { files: [img] } });

    const btn = screen.getByText('Extract Recipe');
    await userEvent.click(btn);

    await waitFor(() => expect(mockNavigate).toHaveBeenCalled());
  });

  it('navigates to signed_url when stream completes with a safe URL', async () => {
    const onClose = vi.fn();
    mockExtractStream.mockImplementation(
      async (_files: File[], _onProgress: any, onComplete: any) => {
        // simulate server returning safe signed_url
        onComplete('/recipes/new?ai=1&draftId=abc', 'abc');
        return new AbortController();
      }
    );

    render(<AddByPhotoModal isOpen={true} onClose={onClose} />);

    const input = document.querySelector(
      'input[type=file]'
    ) as HTMLInputElement;
    const img = new File(['i'], 'i.jpg', { type: 'image/jpeg' });
    fireEvent.change(input, { target: { files: [img] } });

    const btn = screen.getByText('Extract Recipe');
    await userEvent.click(btn);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith(
        '/recipes/new?ai=1&draftId=abc'
      );
      expect(onClose).toHaveBeenCalled();
    });
  });
});
