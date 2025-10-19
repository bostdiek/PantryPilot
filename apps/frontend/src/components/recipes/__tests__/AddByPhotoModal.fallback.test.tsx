import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AddByPhotoModal } from '../AddByPhotoModal';

// Shared mocks
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

// Auth & recipe stores
vi.mock('../../../stores/useAuthStore', () => ({
  useIsAuthenticated: () => true,
  useAuthStore: { getState: () => ({ token: 'tok' }) },
}));
vi.mock('../../../stores/useRecipeStore', () => ({
  useRecipeStore: { getState: () => ({ setFormFromSuggestion: vi.fn() }) },
}));

// Media query & logger
vi.mock('../../../hooks/useMediaQuery', () => ({ useIsMobile: () => false }));
vi.mock('../../../lib/logger', () => ({
  logger: { debug: vi.fn(), warn: vi.fn(), error: vi.fn() },
}));

// Thumbnail generation (avoid canvas/image complexity)
vi.mock('../../../utils/generateImageThumbnail', () => ({
  generateImageThumbnail: vi.fn().mockResolvedValue(null),
}));

// Dynamic mocks for endpoints
const mockStream = vi.fn();
const mockPost = vi.fn();
const mockIsSafe = vi.fn();
vi.mock('../../../api/endpoints/aiDrafts', () => ({
  extractRecipeFromImageStream: (...args: any[]) => mockStream(...args),
  extractRecipeFromImage: (...args: any[]) => mockPost(...args),
  isSafeInternalPath: (url: string) => mockIsSafe(url),
}));

function addTestFile() {
  const input = screen.getByLabelText(/choose files/i) as HTMLInputElement;
  const file = new File(['data'], 'photo.jpg', { type: 'image/jpeg' });
  fireEvent.change(input, { target: { files: [file] } });
  return file;
}

beforeEach(() => {
  vi.clearAllMocks();
  mockIsSafe.mockReturnValue(true);
});

describe('AddByPhotoModal fallback & safety paths', () => {
  it('falls back to POST when streaming throws and navigates to signed_url', async () => {
    mockStream.mockRejectedValue(new Error('stream fail'));
    mockPost.mockResolvedValue({
      signed_url: '/recipes/new?ai=1&draftId=fallback2',
      draft_id: 'fallback2',
    });

    render(
      <BrowserRouter>
        <AddByPhotoModal isOpen onClose={vi.fn()} />
      </BrowserRouter>
    );

    addTestFile();

    await userEvent.click(
      screen.getByRole('button', { name: /extract recipe/i })
    );

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalled();
      expect(mockNavigate).toHaveBeenCalledWith(
        '/recipes/new?ai=1&draftId=fallback2'
      );
    });
  });

  it('uses fallback internal path when signed_url is unsafe', async () => {
    mockIsSafe.mockReturnValue(false);
    mockStream.mockImplementation(
      async (_files: File[], _onProgress: any, onComplete: any) => {
        onComplete('/outside/path', 'abc123');
        return new AbortController();
      }
    );

    render(
      <BrowserRouter>
        <AddByPhotoModal isOpen onClose={vi.fn()} />
      </BrowserRouter>
    );

    addTestFile();

    await userEvent.click(
      screen.getByRole('button', { name: /extract recipe/i })
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith(
        '/recipes/new?ai=1&draftId=abc123'
      );
    });
  });
});
