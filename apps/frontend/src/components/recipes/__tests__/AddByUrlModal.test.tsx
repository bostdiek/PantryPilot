import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// Mocks for dependencies
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<any>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockSetFormFromSuggestion = vi.fn();
vi.mock('../../../stores/useRecipeStore', () => ({
  useRecipeStore: {
    getState: () => ({ setFormFromSuggestion: mockSetFormFromSuggestion }),
  },
}));

vi.mock('../../../lib/logger', () => ({
  logger: { info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}));

// Mock aiDrafts endpoints
const mockExtractStream = vi.fn();
const mockExtractPost = vi.fn();
const mockGetDraft = vi.fn();

vi.mock('../../../api/endpoints/aiDrafts', () => ({
  extractRecipeStreamFetch: (...args: any[]) => mockExtractStream(...args),
  extractRecipeFromUrl: (...args: any[]) => mockExtractPost(...args),
  getDraftByIdOwner: (...args: any[]) => mockGetDraft(...args),
}));

import { AddByUrlModal } from '../AddByUrlModal';

// Helper to render with router context
const renderWithRouter = (ui: React.ReactElement) => {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
};

describe('AddByUrlModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    // cleanup rendered DOM
    document.body.innerHTML = '';
  });

  it('renders form fields and buttons', () => {
    renderWithRouter(<AddByUrlModal isOpen={true} onClose={() => {}} />);

    expect(screen.getByLabelText(/Recipe URL/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Extract Recipe/i })
    ).toBeInTheDocument();
  });

  it('shows validation error when URL is empty or invalid', async () => {
    const user = userEvent.setup();
    renderWithRouter(<AddByUrlModal isOpen={true} onClose={() => {}} />);

    // Submit without entering URL using form submit to avoid HTML5 validation
    const form = document.querySelector('form') as HTMLFormElement;
    fireEvent.submit(form);
    expect(await screen.findByText(/Please enter a URL/i)).toBeInTheDocument();

    // Enter invalid URL and submit
    await user.type(screen.getByLabelText(/Recipe URL/i), 'not-a-url');
    fireEvent.submit(form);
    expect(
      await screen.findByText(/Please enter a valid URL/i)
    ).toBeInTheDocument();
  });

  it('handles successful streaming flow and navigates to new recipe with AI flag', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    // Mock streaming function: it will call progress callback and then the completion callback with draftId
    mockExtractStream.mockImplementation(
      async (
        url: string,
        _token: any,
        onProgress: (ev: any) => void,
        onComplete: (signedUrl: string | null, draftId?: string) => void,
        _onError: (err: any) => void
      ) => {
        // Simulate progress events
        onProgress({ status: 'started' });
        onProgress({ status: 'fetching' });
        // Simulate immediate completion with draftId for deterministic test
        onComplete(null, 'draft-123');
        // Return an AbortController stub
        return new AbortController();
      }
    );

    // getDraftByIdOwner should return a draft-like payload
    mockGetDraft.mockResolvedValue({ payload: { title: 'AI Recipe' } });

    renderWithRouter(<AddByUrlModal isOpen={true} onClose={onClose} />);

    await user.type(
      screen.getByLabelText(/Recipe URL/i),
      'https://example.com/recipe'
    );
    const form = document.querySelector('form') as HTMLFormElement;
    fireEvent.submit(form);

    // Wait for navigation to be called with the AI new recipe route
    await waitFor(() => {
      expect(mockGetDraft).toHaveBeenCalledWith('draft-123');
      expect(mockSetFormFromSuggestion).toHaveBeenCalledWith({
        title: 'AI Recipe',
      });
      expect(mockNavigate).toHaveBeenCalledWith('/recipes/new?ai=1');
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('falls back to POST when streaming fails and navigates to signed_url', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    // Streaming fails by throwing or invoking onError; make it throw
    mockExtractStream.mockImplementation(async () => {
      throw new Error('stream error');
    });

    // Fallback POST should return signed_url
    mockExtractPost.mockResolvedValue({ signed_url: '/signed/redirect' });

    renderWithRouter(<AddByUrlModal isOpen={true} onClose={onClose} />);

    await user.type(
      screen.getByLabelText(/Recipe URL/i),
      'https://example.com/recipe'
    );
    const form = document.querySelector('form') as HTMLFormElement;
    fireEvent.submit(form);

    await waitFor(() => {
      expect(mockExtractPost).toHaveBeenCalledWith(
        'https://example.com/recipe',
        undefined
      );
      expect(mockNavigate).toHaveBeenCalledWith('/signed/redirect');
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('handles streaming completion that returns a signed_url and navigates there', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    mockExtractStream.mockImplementation(
      async (
        url: string,
        _token: any,
        onProgress: (ev: any) => void,
        onComplete: (signedUrl: string | null, draftId?: string) => void,
        _onError: (err: any) => void
      ) => {
        onProgress({ status: 'started' });
        // Return a signed URL from the streaming completion
        onComplete('/signed/stream-redirect', undefined as any);
        return new AbortController();
      }
    );

    renderWithRouter(<AddByUrlModal isOpen={true} onClose={onClose} />);

    await user.type(
      screen.getByLabelText(/Recipe URL/i),
      'https://example.com/recipe'
    );
    const form = document.querySelector('form') as HTMLFormElement;
    fireEvent.submit(form);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/signed/stream-redirect');
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('shows error when draft fetch fails after streaming completes with draftId', async () => {
    const user = userEvent.setup();

    mockExtractStream.mockImplementation(
      async (
        url: string,
        _token: any,
        onProgress: (ev: any) => void,
        onComplete: (signedUrl: string | null, draftId?: string) => void,
        _onError: (err: any) => void
      ) => {
        onProgress({ status: 'started' });
        // Complete with draft id but subsequent getDraft will fail
        onComplete(null, 'draft-456');
        return new AbortController();
      }
    );

    mockGetDraft.mockRejectedValue(new Error('failed to fetch draft'));

    renderWithRouter(<AddByUrlModal isOpen={true} onClose={() => {}} />);

    await user.type(
      screen.getByLabelText(/Recipe URL/i),
      'https://example.com/recipe'
    );
    const form = document.querySelector('form') as HTMLFormElement;
    fireEvent.submit(form);

    // Should show friendly error message from component
    expect(
      await screen.findByText(
        /Failed to load extracted recipe. Please try again\./i
      )
    ).toBeInTheDocument();
    // Ensure navigation did not occur
    expect(mockNavigate).not.toHaveBeenCalledWith('/recipes/new?ai=1');
  });

  it('shows API error message when POST fallback fails', async () => {
    const user = userEvent.setup();

    mockExtractStream.mockImplementation(async () => {
      throw new Error('stream error');
    });

    mockExtractPost.mockRejectedValue({ message: 'POST failed' });

    renderWithRouter(<AddByUrlModal isOpen={true} onClose={() => {}} />);

    await user.type(
      screen.getByLabelText(/Recipe URL/i),
      'https://example.com/recipe'
    );
    const form = document.querySelector('form') as HTMLFormElement;
    fireEvent.submit(form);

    expect(await screen.findByText(/POST failed/i)).toBeInTheDocument();
  });
});
