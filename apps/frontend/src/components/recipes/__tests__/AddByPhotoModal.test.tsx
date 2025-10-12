import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuthStore } from '../../../stores/useAuthStore';
import { useRecipeStore } from '../../../stores/useRecipeStore';
import { AddByPhotoModal } from '../AddByPhotoModal';

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
  extractRecipeFromImageStream: (...args: any[]) =>
    mockExtractImageStream(...args),
  getDraftByIdOwner: (...args: any[]) => mockGetDraft(...args),
  isSafeInternalPath: (url: string) => {
    // Mock implementation matching the real function
    try {
      const absoluteUrl = new URL(url, window.location.origin);
      return (
        absoluteUrl.origin === window.location.origin &&
        absoluteUrl.pathname.startsWith('/recipes')
      );
    } catch {
      return false;
    }
  },
}));

vi.mock('../../../lib/logger', () => ({
  logger: { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() },
}));

describe('AddByPhotoModal', () => {
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Reset auth store to authenticated state
    useAuthStore.setState({
      token: 'test-token',
      user: { id: '1', username: 'test', email: 'test@test.com' },
    });
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

  it('renders modal when open', async () => {
    renderModal();
    expect(screen.getByText('Upload Recipe Photo')).toBeInTheDocument();
    // Wait for the button text which includes an emoji to appear
    await screen.findByText(/Select Photo/);
  });

  it('does not render when closed', () => {
    renderModal(false);
    expect(screen.queryByText('Upload Recipe Photo')).not.toBeInTheDocument();
  });

  it('shows file selection button initially', () => {
    renderModal();
    expect(screen.getByText('📷 Select Photos')).toBeInTheDocument();
  });

  it('validates file type on selection', async () => {
    renderModal();

    // Create a non-image file and dispatch change event directly (bypass accept)
    const file = new File(['test'], 'test.txt', { type: 'text/plain' });
    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    // Simulate change event with files (user.upload respects accept which would block this)
    fireEvent.change(input, { target: { files: [file] } });

    // Use findByText to wait for the error to appear in the DOM
    await screen.findByText(/Please select only image files/);
  });

  it('validates file size on selection', async () => {
    const user = userEvent.setup();
    renderModal();

    // Create a large file (> 8 MiB)
    const largeFile = new File(['x'.repeat(9 * 1024 * 1024)], 'large.jpg', {
      type: 'image/jpeg',
    });
    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;

    await user.upload(input, largeFile);

    await waitFor(() => {
      expect(
        screen.getByText(/File size too large\. Max 8 MiB per file/)
      ).toBeInTheDocument();
    });
  });

  it('accepts valid image file', async () => {
    const user = userEvent.setup();
    renderModal();

    const file = new File(['image'], 'test.jpg', { type: 'image/jpeg' });
    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;

    await user.upload(input, file);

    await waitFor(() => {
      expect(screen.getByText(/1\. test\.jpg/)).toBeInTheDocument();
    });
  });

  it('redirects to login if not authenticated', async () => {
    const user = userEvent.setup();
    // Set unauthenticated state
    useAuthStore.setState({ token: null, user: null });

    renderModal();

    const file = new File(['image'], 'test.jpg', { type: 'image/jpeg' });
    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    await user.upload(input, file);

    const extractButton = screen.getByRole('button', {
      name: /Extract Recipe/i,
    });
    await user.click(extractButton);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith(
        expect.stringContaining('/login?next=')
      );
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
      async (_file, _onProgress, onComplete) => {
        onComplete('', 'draft-123');
        return new AbortController();
      }
    );

    mockGetDraft.mockResolvedValue(mockDraftResponse);

    renderModal();

    const file = new File(['image'], 'test.jpg', { type: 'image/jpeg' });
    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    await user.upload(input, file);

    const extractButton = screen.getByRole('button', {
      name: /Extract Recipe/i,
    });
    await user.click(extractButton);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith(
        '/recipes/new?ai=1&draftId=draft-123'
      );
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
    mockExtractImageStream.mockRejectedValue(new Error('Streaming failed'));

    // Mock POST fallback to succeed
    mockExtractImage.mockResolvedValue(mockResponse);

    renderModal();

    const file = new File(['image'], 'test.jpg', { type: 'image/jpeg' });
    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    await user.upload(input, file);

    const extractButton = screen.getByRole('button', {
      name: /Extract Recipe/i,
    });
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
      async (_file, _onProgress, _onComplete, onError) => {
        onError(error as any);
        return new AbortController();
      }
    );

    renderModal();

    const file = new File(['image'], 'test.jpg', { type: 'image/jpeg' });
    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    await user.upload(input, file);

    const extractButton = screen.getByRole('button', {
      name: /Extract Recipe/i,
    });
    await user.click(extractButton);

    await waitFor(() => {
      expect(screen.getByText(/File size is too large/)).toBeInTheDocument();
    });
  });

  it('handles 415 error (unsupported media type)', async () => {
    const user = userEvent.setup();
    const error = {
      message:
        'Unsupported file type. Please upload an image file (JPEG, PNG, etc.).',
      status: 415,
      code: 'unsupported_media_type',
    };

    mockExtractImageStream.mockImplementation(
      async (_file, _onProgress, _onComplete, onError) => {
        onError(error as any);
        return new AbortController();
      }
    );

    renderModal();

    const file = new File(['image'], 'test.jpg', { type: 'image/jpeg' });
    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    await user.upload(input, file);

    const extractButton = screen.getByRole('button', {
      name: /Extract Recipe/i,
    });
    await user.click(extractButton);

    await waitFor(() => {
      expect(screen.getByText(/Unsupported file type/)).toBeInTheDocument();
    });
  });

  it('displays progress messages during streaming', async () => {
    mockExtractImageStream.mockImplementation(
      async (_file, onProgress, onComplete) => {
        onProgress({
          status: 'started',
          step: 'init',
          detail: 'Starting extraction...',
        });
        onProgress({
          status: 'ai_call',
          step: 'ai',
          detail: 'Analyzing image...',
        });
        // Delay completion so the component can render progress messages first
        setTimeout(() => onComplete('', 'draft-789'), 0);
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
    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    // Use a direct change event to reliably set the file in tests
    fireEvent.change(input, { target: { files: [file] } });

    const extractButton = screen.getByRole('button', {
      name: /Extract Recipe/i,
    });
    fireEvent.click(extractButton);

    // Wait for the loading/progress area to render (less brittle than matching a single SSE message)
    await screen.findByText(/Extracting recipe from image/);
  });

  it('allows changing file selection by clearing and selecting new files', async () => {
    const user = userEvent.setup();
    renderModal();

    const file1 = new File(['image1'], 'test1.jpg', { type: 'image/jpeg' });
    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    await user.upload(input, file1);

    await waitFor(() => {
      expect(screen.getByText(/1\. test1\.jpg/)).toBeInTheDocument();
    });

    // Clear all files
    const clearButton = screen.getByRole('button', { name: /Clear All/i });
    await user.click(clearButton);

    await waitFor(() => {
      expect(screen.getByText('📷 Select Photos')).toBeInTheDocument();
    });

    // Select new file
    const file2 = new File(['image2'], 'test2.jpg', { type: 'image/jpeg' });
    await user.upload(input, file2);

    await waitFor(() => {
      expect(screen.getByText(/1\. test2\.jpg/)).toBeInTheDocument();
      expect(screen.queryByText(/test1\.jpg/)).not.toBeInTheDocument();
    });
  });

  it('closes modal when cancel button is clicked', async () => {
    const user = userEvent.setup();
    renderModal();

    const cancelButton = screen.getByText('Cancel');
    await user.click(cancelButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('validates signed URL and uses fallback for unsafe URLs', async () => {
    const user = userEvent.setup();
    const unsafeUrl = 'https://evil.com/steal-data';

    // Mock streaming to return unsafe URL
    mockExtractImageStream.mockImplementation(
      async (_file, _onProgress, onComplete) => {
        onComplete(unsafeUrl, 'draft-unsafe');
        return new AbortController();
      }
    );

    renderModal();

    const file = new File(['image'], 'test.jpg', { type: 'image/jpeg' });
    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    await user.upload(input, file);

    const extractButton = screen.getByRole('button', {
      name: /Extract Recipe/i,
    });
    await user.click(extractButton);

    // Should navigate to safe fallback, not the unsafe URL
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith(
        '/recipes/new?ai=1&draftId=draft-unsafe'
      );
      expect(mockNavigate).not.toHaveBeenCalledWith(unsafeUrl);
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  it('accepts safe internal signed URLs', async () => {
    const user = userEvent.setup();
    const safeUrl = '/recipes/new?ai=1&draftId=draft-safe&token=jwt';

    // Mock streaming to return safe URL
    mockExtractImageStream.mockImplementation(
      async (_file, _onProgress, onComplete) => {
        onComplete(safeUrl, 'draft-safe');
        return new AbortController();
      }
    );

    renderModal();

    const file = new File(['image'], 'test.jpg', { type: 'image/jpeg' });
    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    await user.upload(input, file);

    const extractButton = screen.getByRole('button', {
      name: /Extract Recipe/i,
    });
    await user.click(extractButton);

    // Should navigate to the safe URL as-is
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith(safeUrl);
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  // Multiple file tests
  it('accepts multiple image files', async () => {
    const user = userEvent.setup();
    renderModal();

    const file1 = new File(['image1'], 'test1.jpg', { type: 'image/jpeg' });
    const file2 = new File(['image2'], 'test2.jpg', { type: 'image/jpeg' });
    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;

    await user.upload(input, [file1, file2]);

    await waitFor(() => {
      expect(screen.getByText('2 files selected')).toBeInTheDocument();
      expect(screen.getByText(/1\. test1\.jpg/)).toBeInTheDocument();
      expect(screen.getByText(/2\. test2\.jpg/)).toBeInTheDocument();
    });
  });

  it('validates combined file size for multiple files', async () => {
    const user = userEvent.setup();
    renderModal();

    // Create files that individually are under 8MiB but combined exceed 20MiB
    // Each file is 7 MiB, total is 21 MiB which exceeds 20 MiB limit
    const file1 = new File(['x'.repeat(7 * 1024 * 1024)], 'large1.jpg', {
      type: 'image/jpeg',
    });
    const file2 = new File(['x'.repeat(7 * 1024 * 1024)], 'large2.jpg', {
      type: 'image/jpeg',
    });
    const file3 = new File(['x'.repeat(7 * 1024 * 1024)], 'large3.jpg', {
      type: 'image/jpeg',
    });
    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;

    await user.upload(input, [file1, file2, file3]);

    await waitFor(() => {
      expect(
        screen.getByText(/Combined file size .* exceeds limit of 20 MiB/)
      ).toBeInTheDocument();
    });
  });

  it('validates individual file size in multiple file selection', async () => {
    const user = userEvent.setup();
    renderModal();

    const file1 = new File(['image1'], 'test1.jpg', { type: 'image/jpeg' });
    const file2 = new File(['x'.repeat(9 * 1024 * 1024)], 'large.jpg', {
      type: 'image/jpeg',
    });
    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;

    await user.upload(input, [file1, file2]);

    await waitFor(() => {
      expect(
        screen.getByText(/File size too large\. Max 8 MiB per file/)
      ).toBeInTheDocument();
    });
  });

  it('allows removing individual files from selection', async () => {
    const user = userEvent.setup();
    renderModal();

    const file1 = new File(['image1'], 'test1.jpg', { type: 'image/jpeg' });
    const file2 = new File(['image2'], 'test2.jpg', { type: 'image/jpeg' });
    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;

    await user.upload(input, [file1, file2]);

    await waitFor(() => {
      expect(screen.getByText('2 files selected')).toBeInTheDocument();
    });

    // Find and click the remove button for the first file
    const removeButtons = screen.getAllByRole('button', { name: /Remove/ });
    await user.click(removeButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('1 file selected')).toBeInTheDocument();
      expect(screen.queryByText(/1\. test1\.jpg/)).not.toBeInTheDocument();
      expect(screen.getByText(/1\. test2\.jpg/)).toBeInTheDocument();
    });
  });

  it('allows clearing all selected files', async () => {
    const user = userEvent.setup();
    renderModal();

    const file1 = new File(['image1'], 'test1.jpg', { type: 'image/jpeg' });
    const file2 = new File(['image2'], 'test2.jpg', { type: 'image/jpeg' });
    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;

    await user.upload(input, [file1, file2]);

    await waitFor(() => {
      expect(screen.getByText('2 files selected')).toBeInTheDocument();
    });

    const clearButton = screen.getByRole('button', { name: /Clear All/i });
    await user.click(clearButton);

    await waitFor(() => {
      expect(screen.getByText('📷 Select Photos')).toBeInTheDocument();
      expect(screen.queryByText('2 files selected')).not.toBeInTheDocument();
    });
  });

  it('allows adding more files to existing selection', async () => {
    const user = userEvent.setup();
    renderModal();

    const file1 = new File(['image1'], 'test1.jpg', { type: 'image/jpeg' });
    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;

    await user.upload(input, file1);

    await waitFor(() => {
      expect(screen.getByText('1 file selected')).toBeInTheDocument();
    });

    const addMoreButton = screen.getByRole('button', { name: /Add More/i });
    await user.click(addMoreButton);

    const file2 = new File(['image2'], 'test2.jpg', { type: 'image/jpeg' });
    await user.upload(input, file2);

    await waitFor(() => {
      expect(screen.getByText('2 files selected')).toBeInTheDocument();
      expect(screen.getByText(/1\. test1\.jpg/)).toBeInTheDocument();
      expect(screen.getByText(/2\. test2\.jpg/)).toBeInTheDocument();
    });
  });

  it('shows total file size for multiple files', async () => {
    const user = userEvent.setup();
    renderModal();

    // Create files with known sizes
    const file1 = new File(['x'.repeat(1024 * 1024)], 'test1.jpg', {
      type: 'image/jpeg',
    }); // 1 MiB
    const file2 = new File(['x'.repeat(2 * 1024 * 1024)], 'test2.jpg', {
      type: 'image/jpeg',
    }); // 2 MiB
    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;

    await user.upload(input, [file1, file2]);

    await waitFor(() => {
      expect(screen.getByText('2 files selected')).toBeInTheDocument();
      expect(screen.getByText(/Total: 3\.00 MiB/)).toBeInTheDocument();
    });
  });
});
