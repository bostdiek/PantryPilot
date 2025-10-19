import '@testing-library/jest-dom';
import { fireEvent, render, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AddByPhotoModal } from './AddByPhotoModal';

// Mock react-router navigate
vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

// Mock auth store hooks
vi.mock('../../stores/useAuthStore', () => ({
  useIsAuthenticated: () => mockIsAuthenticated.value,
  useAuthStore: {
    getState: () => ({
      logout: vi.fn(),
    }),
  },
}));

// Mock recipe store
vi.mock('../../stores/useRecipeStore', () => ({
  useRecipeStore: {
    getState: () => ({
      setFormFromSuggestion: vi.fn(),
    }),
  },
}));

// Mock aiDrafts endpoints used inside component
const mockStreamImpl = vi.fn();
const mockPostImpl = vi.fn();
const mockGetDraftOwner = vi.fn();
const mockIsSafePath = vi.fn().mockReturnValue(true);
vi.mock('../../api/endpoints/aiDrafts', () => ({
  extractRecipeFromImageStream: (...args: any[]) => mockStreamImpl(...args),
  extractRecipeFromImage: (...args: any[]) => mockPostImpl(...args),
  getDraftByIdOwner: (...args: any[]) => mockGetDraftOwner(...args),
  isSafeInternalPath: (url: string) => mockIsSafePath(url),
}));

// Provide minimal global URL APIs for useImageSelection previews
beforeEach(() => {
  (global as any).URL = (global as any).URL || {};
  (global as any).URL.createObjectURL = vi.fn().mockImplementation((blob) => {
    // Include name if possible to make assertions easier
    return typeof blob === 'object' && 'name' in blob
      ? `blob:${(blob as any).name}`
      : 'blob:test';
  });
  (global as any).URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
  vi.clearAllMocks();
});

const mockNavigate = vi.fn();
const mockIsAuthenticated = { value: true };

function createImageFile(
  name: string,
  sizeBytes = 50_000,
  type = 'image/png'
): File {
  const blob = new Blob([new Uint8Array(sizeBytes)], { type });
  return new File([blob], name, { type });
}

describe('AddByPhotoModal basic rendering & selection', () => {
  it('shows camera and file chooser buttons initially and disabled submit', () => {
    const onClose = vi.fn();
    const { getByRole, queryByText } = render(
      <AddByPhotoModal isOpen={true} onClose={onClose} />
    );
    expect(getByRole('button', { name: /Take Photo/i })).toBeInTheDocument();
    expect(
      getByRole('button', { name: /Open file chooser/i })
    ).toBeInTheDocument();
    const extractBtn = getByRole('button', { name: /Extract Recipe/i });
    expect(extractBtn).toBeDisabled();
    // No files summary yet
    expect(queryByText(/file selected/)).toBeNull();
  });

  it('selects a file and enables submit', async () => {
    const onClose = vi.fn();
    const { getByLabelText, getByRole, findByText } = render(
      <AddByPhotoModal isOpen={true} onClose={onClose} />
    );
    const fileInput = getByLabelText('Choose files');
    const file = createImageFile('test.png');
    // Fire change event with a FileList simulation
    fireEvent.change(fileInput, { target: { files: [file] } });
    // Wait for summary text
    await findByText(/1 file selected/);
    const extractBtn = getByRole('button', { name: /Extract Recipe/i });
    expect(extractBtn).toBeEnabled();
  });
});

describe('AddByPhotoModal handleUpload authentication', () => {
  it('redirects to login when unauthenticated', async () => {
    mockIsAuthenticated.value = false;
    const onClose = vi.fn();
    const { getByLabelText, getByRole, findByText } = render(
      <AddByPhotoModal isOpen={true} onClose={onClose} />
    );
    const fileInput = getByLabelText('Choose files');
    fireEvent.change(fileInput, {
      target: { files: [createImageFile('a.png')] },
    });
    await findByText(/1 file selected/);
    fireEvent.click(getByRole('button', { name: /Extract Recipe/i }));
    expect(mockNavigate).toHaveBeenCalled();
    const dest = mockNavigate.mock.calls[0][0];
    expect(dest).toMatch(/\/login\?next=/);
  });
});

describe('AddByPhotoModal streaming success paths', () => {
  beforeEach(() => {
    mockIsAuthenticated.value = true; // ensure logged in
  });

  it('navigates to safe signed_url on streaming completion', async () => {
    mockStreamImpl.mockImplementation(
      async (
        files: File[],
        onProgress: (e: any) => void,
        onComplete: (signed: string, draft: string) => void,
        _onError: any
      ) => {
        onProgress({ detail: 'step', status: 'progress' });
        onComplete('/recipes/new?ai=1&draftId=abc', 'abc');
        return new AbortController();
      }
    );
    const onClose = vi.fn();
    const { getByLabelText, getByRole, findByText } = render(
      <AddByPhotoModal isOpen={true} onClose={onClose} />
    );
    fireEvent.change(getByLabelText('Choose files'), {
      target: { files: [createImageFile('ok.png')] },
    });
    await findByText(/1 file selected/);
    fireEvent.click(getByRole('button', { name: /Extract Recipe/i }));
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith(
        '/recipes/new?ai=1&draftId=abc'
      );
    });
    expect(onClose).toHaveBeenCalled();
  });

  it('falls back when signed_url unsafe', async () => {
    mockIsSafePath.mockReturnValue(false);
    mockStreamImpl.mockImplementation(
      async (
        files: File[],
        onProgress: (e: any) => void,
        onComplete: (signed: string, draft: string) => void
      ) => {
        onProgress({ detail: 'progress', status: 'progress' });
        onComplete('/malicious', 'xyz');
        return new AbortController();
      }
    );
    const onClose = vi.fn();
    const { getByLabelText, getByRole, findByText } = render(
      <AddByPhotoModal isOpen={true} onClose={onClose} />
    );
    fireEvent.change(getByLabelText('Choose files'), {
      target: { files: [createImageFile('ok2.png')] },
    });
    await findByText(/1 file selected/);
    fireEvent.click(getByRole('button', { name: /Extract Recipe/i }));
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith(
        '/recipes/new?ai=1&draftId=xyz'
      );
    });
  });
});

describe('AddByPhotoModal camera preview error handling', () => {
  it('shows error when getUserMedia rejects (desktop camera)', async () => {
    mockIsAuthenticated.value = true;
    // Mock mediaDevices.getUserMedia to reject
    (navigator as any).mediaDevices = {
      getUserMedia: vi.fn().mockRejectedValue(new Error('no camera')),
    };
    const onClose = vi.fn();
    const { getByRole, findByText } = render(
      <AddByPhotoModal isOpen={true} onClose={onClose} />
    );
    fireEvent.click(getByRole('button', { name: /Take Photo/i }));
    // Expect error surfaced (from effect)
    const err = await findByText(/Unable to access camera/i);
    expect(err).toBeInTheDocument();
  });
});
