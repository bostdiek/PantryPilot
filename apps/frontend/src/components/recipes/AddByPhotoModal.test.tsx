import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

// Mock hooks and heavy dependencies used by the component to keep test focused
vi.mock('../../hooks/useMediaQuery', () => ({
  useIsMobile: () => false,
}));

vi.mock('../../stores/useAuthStore', () => ({
  useIsAuthenticated: () => true,
}));

vi.mock('../../api/endpoints/aiDrafts', () => ({
  extractRecipeFromImage: vi.fn(),
  extractRecipeFromImageStream: vi.fn(),
  getDraftByIdOwner: vi.fn(),
  isSafeInternalPath: vi.fn(),
}));

// Keep navigation stubbed
vi.mock('react-router-dom', async () => {
  const actual =
    await vi.importActual<typeof import('react-router-dom')>(
      'react-router-dom'
    );
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  };
});

import { AddByPhotoModal } from './AddByPhotoModal';

describe('AddByPhotoModal', () => {
  beforeEach(() => {
    // Nothing for now
  });

  it('does not show an error when the file picker is cancelled (empty FileList)', () => {
    const onClose = vi.fn();

    render(<AddByPhotoModal isOpen={true} onClose={onClose} />);

    // The file input has aria-label "Choose files"
    const input = screen.getByLabelText('Choose files') as HTMLInputElement;
    expect(input).toBeTruthy();

    // Simulate cancelling the file picker: empty FileList
    fireEvent.change(input, { target: { files: [] } });

    // The component previously set an error on cancel; ensure no error message is shown
    expect(
      screen.queryByText(
        /Please select only image files|Please select at least one file/i
      )
    ).toBeNull();
  });
});
