import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { AddByPhotoModal } from '../AddByPhotoModal';
import { useAuthStore } from '../../../stores/useAuthStore';
import { useRecipeStore } from '../../../stores/useRecipeStore';

// Mock navigation
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock the API functions
const mockExtractImage = vi.fn();
const mockExtractImageStream = vi.fn();
const mockGetDraft = vi.fn();

vi.mock('../../../api/endpoints/aiDrafts', () => ({
  extractRecipeFromImage: (...args: any[]) => mockExtractImage(...args),
  extractRecipeFromImageStream: (...args: any[]) => mockExtractImageStream(...args),
  getDraftByIdOwner: (...args: any[]) => mockGetDraft(...args),
}));

vi.mock('../../../lib/logger', () => ({
  logger: { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() },
}));

describe('AddByPhotoModal', () => {
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Reset auth store to authenticated state
    useAuthStore.setState({ token: 'test-token', user: { id: '1', username: 'test', email: 'test@test.com' } });
    // Reset recipe store
    useRecipeStore.setState({ formSuggestion: null, isAISuggestion: false });
  });

  afterEach(() => {
    // cleanup rendered DOM
    document.body.innerHTML = '';
  });

  const renderModal = (isOpen = true) => {
    return render(
      <BrowserRouter>
        <AddByPhotoModal isOpen={isOpen} onClose={mockOnClose} />
      </BrowserRouter>
    );
  };

  it('renders modal when open', () => {
    renderModal();
    expect(screen.getByText('Upload Recipe Photo')).toBeInTheDocument();
    expect(screen.getByText('Select Photo')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    renderModal(false);
    expect(screen.queryByText('Upload Recipe Photo')).not.toBeInTheDocument();
  });

  it('shows file selection button initially', () => {
    renderModal();
    expect(screen.getByText('📷 Select Photo')).toBeInTheDocument();
  });

  it('validates file type on selection', async () => {
    const user = userEvent.setup();
    renderModal();

    // Create a non-image file
    const file = new File(['test'], 'test.txt', { type: 'text/plain' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    await user.upload(input, file);

    await waitFor(() => {
      expect(screen.getByText(/Please select an image file/)).toBeInTheDocument();
    });
  });

  it('validates file size on selection', async () => {
    const user = userEvent.setup();
    renderModal();

    // Create a large file (> 10MB)
    const largeFile = new File(['x'.repeat(11 * 1024 * 1024)], 'large.jpg', { type: 'image/jpeg' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    await user.upload(input, largeFile);

    await waitFor(() => {
      expect(screen.getByText('File size is too large. Please select an image under 10MB.')).toBeInTheDocument();
    });
  });

  it('accepts valid image file', async () => {
    const user = userEvent.setup();
    renderModal();

    const file = new File(['image'], 'test.jpg', { type: 'image/jpeg' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    await user.upload(input, file);

    await waitFor(() => {
      expect(screen.getByText('test.jpg')).toBeInTheDocument();
    });
  });

  it('redirects to login if not authenticated', async () => {
    const user = userEvent.setup();
    // Set unauthenticated state
    useAuthStore.setState({ token: null, user: null });
    
    renderModal();

    const file = new File(['image'], 'test.jpg', { type: 'image/jpeg' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, file);

    const extractButton = screen.getByRole('button', { name: /Extract Recipe/i });
    await user.click(extractButton);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith(expect.stringContaining('/login?next='));
    });
  });

  it('handles successful streaming extraction', async () => {
    const user = userEvent.setup();
    const mockDraftResponse = {
      payload: {
        generated_recipe: {
          recipe_data: { title: 'Test Recipe' },
          confidence_score: 0.9,
          extraction_notes: null,
          source_url: 'test.jpg',
        },
        extraction_metadata: {
          source_url: 'test.jpg',
          extracted_at: new Date().toISOString(),
        },
      },
      type: 'recipe_suggestion' as const,
      created_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + 3600000).toISOString(),
    };

    // Mock streaming to immediately call onComplete
    mockExtractImageStream.mockImplementation(
      async (_file, _prompt, _onProgress, onComplete) => {
        onComplete('', 'draft-123');
        return new AbortController();
      }
    );

    mockGetDraft.mockResolvedValue(mockDraftResponse);

    renderModal();

    const file = new File(['image'], 'test.jpg', { type: 'image/jpeg' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, file);

    const extractButton = screen.getByRole('button', { name: /Extract Recipe/i });
    await user.click(extractButton);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/recipes/new?ai=1&draftId=draft-123');
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  it('falls back to POST when streaming fails', async () => {
    const user = userEvent.setup();
    const mockResponse = {
      draft_id: 'draft-456',
      signed_url: '/recipes/new?ai=1&draftId=draft-456&token=test-token',
      expires_at: new Date(Date.now() + 3600000).toISOString(),
      ttl_seconds: 3600,
    };

    // Mock streaming to throw error
    mockExtractImageStream.mockRejectedValue(
      new Error('Streaming failed')
    );

    // Mock POST fallback to succeed
    mockExtractImage.mockResolvedValue(mockResponse);

    renderModal();

    const file = new File(['image'], 'test.jpg', { type: 'image/jpeg' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, file);

    const extractButton = screen.getByRole('button', { name: /Extract Recipe/i });
    await user.click(extractButton);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith(mockResponse.signed_url);
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  it('handles 413 error (file too large)', async () => {
    const user = userEvent.setup();
    const error = {
      message: 'File size is too large. Please use a smaller image.',
      status: 413,
      code: 'file_too_large',
    };

    mockExtractImageStream.mockImplementation(
      async (_file, _prompt, _onProgress, _onComplete, onError) => {
        onError(error as any);
        return new AbortController();
      }
    );

    renderModal();

    const file = new File(['image'], 'test.jpg', { type: 'image/jpeg' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, file);

    const extractButton = screen.getByRole('button', { name: /Extract Recipe/i });
    await user.click(extractButton);

    await waitFor(() => {
      expect(screen.getByText(/File size is too large/)).toBeInTheDocument();
    });
  });

  it('handles 415 error (unsupported media type)', async () => {
    const user = userEvent.setup();
    const error = {
      message: 'Unsupported file type. Please upload an image file (JPEG, PNG, etc.).',
      status: 415,
      code: 'unsupported_media_type',
    };

    mockExtractImageStream.mockImplementation(
      async (_file, _prompt, _onProgress, _onComplete, onError) => {
        onError(error as any);
        return new AbortController();
      }
    );

    renderModal();

    const file = new File(['image'], 'test.jpg', { type: 'image/jpeg' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, file);

    const extractButton = screen.getByRole('button', { name: /Extract Recipe/i });
    await user.click(extractButton);

    await waitFor(() => {
      expect(screen.getByText(/Unsupported file type/)).toBeInTheDocument();
    });
  });

  it('displays progress messages during streaming', async () => {
    const user = userEvent.setup();

    mockExtractImageStream.mockImplementation(
      async (_file, _prompt, onProgress, onComplete) => {
        onProgress({ status: 'started', step: 'init', detail: 'Starting extraction...' });
        onProgress({ status: 'ai_call', step: 'ai', detail: 'Analyzing image...' });
        onComplete('', 'draft-789');
        return new AbortController();
      }
    );

    mockGetDraft.mockResolvedValue({
      payload: {
        generated_recipe: null,
        extraction_metadata: {
          source_url: 'test.jpg',
          extracted_at: new Date().toISOString(),
        },
      },
      type: 'recipe_suggestion',
      created_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + 3600000).toISOString(),
    });

    renderModal();

    const file = new File(['image'], 'test.jpg', { type: 'image/jpeg' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, file);

    const extractButton = screen.getByRole('button', { name: /Extract Recipe/i });
    await user.click(extractButton);

    await waitFor(() => {
      expect(screen.getByText(/Starting extraction/)).toBeInTheDocument();
    });
  });

  it('allows changing file selection', async () => {
    const user = userEvent.setup();
    renderModal();

    const file1 = new File(['image1'], 'test1.jpg', { type: 'image/jpeg' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, file1);

    await waitFor(() => {
      expect(screen.getByText('test1.jpg')).toBeInTheDocument();
    });

    const changeButton = screen.getByText('Change');
    await user.click(changeButton);

    const file2 = new File(['image2'], 'test2.jpg', { type: 'image/jpeg' });
    await user.upload(input, file2);

    await waitFor(() => {
      expect(screen.getByText('test2.jpg')).toBeInTheDocument();
    });
  });

  it('closes modal when cancel button is clicked', async () => {
    const user = userEvent.setup();
    renderModal();

    const cancelButton = screen.getByText('Cancel');
    await user.click(cancelButton);

    expect(mockOnClose).toHaveBeenCalled();
  });
});
