import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '../../../stores/useAuthStore';
import { useRecipeStore } from '../../../stores/useRecipeStore';
import { AddByPhotoModal } from '../../recipes/AddByPhotoModal';

// Mock useIsMobile to desktop for integration tests
vi.mock('../../../hooks/useMediaQuery', () => ({ useIsMobile: () => false }));

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({
    token: 't',
    user: { id: '1', username: 'a', email: 'a@a.com' },
  });
  useRecipeStore.setState({ formSuggestion: null, isAISuggestion: false });
});

describe('AddByPhotoModal integration', () => {
  it('uploads file via file input and shows thumbnail', async () => {
    const _user = userEvent.setup();
    render(
      <BrowserRouter>
        <AddByPhotoModal isOpen onClose={vi.fn()} />
      </BrowserRouter>
    );
    const input = screen.getByLabelText(/choose files/i);
    const file = new File(['img'], 'test.jpg', { type: 'image/jpeg' });
    await _user.upload(input, file);
    await waitFor(() => {
      expect(screen.getByText(/1. test.jpg/)).toBeInTheDocument();
      expect(screen.getByAltText(/Preview of test.jpg/)).toBeInTheDocument();
    });
  });

  it('uploads file via camera input and shows thumbnail', async () => {
    const _user = userEvent.setup();
    render(
      <BrowserRouter>
        <AddByPhotoModal isOpen onClose={vi.fn()} />
      </BrowserRouter>
    );
    const cameraInput = document.querySelector(
      'input[capture="environment"]'
    ) as HTMLInputElement;
    const camFile = new File(['img'], 'cam.jpg', { type: 'image/jpeg' });
    await _user.upload(cameraInput, camFile);
    await waitFor(() => {
      expect(screen.getByText(/1. cam.jpg/)).toBeInTheDocument();
      expect(screen.getByAltText(/Preview of cam.jpg/)).toBeInTheDocument();
    });
  });

  it('handles mixed input sources', async () => {
    const _user = userEvent.setup();
    render(
      <BrowserRouter>
        <AddByPhotoModal isOpen onClose={vi.fn()} />
      </BrowserRouter>
    );
    const input = screen.getByLabelText(/choose files/i);
    const cameraInput = document.querySelector(
      'input[capture="environment"]'
    ) as HTMLInputElement;
    const file1 = new File(['img'], 'f1.jpg', { type: 'image/jpeg' });
    const file2 = new File(['img'], 'f2.jpg', { type: 'image/jpeg' });
    await _user.upload(input, file1);
    await _user.upload(cameraInput, file2);
    await waitFor(() => {
      expect(screen.getByText(/1. f1.jpg/)).toBeInTheDocument();
      expect(screen.getByText(/2. f2.jpg/)).toBeInTheDocument();
      expect(screen.getByAltText(/Preview of f1.jpg/)).toBeInTheDocument();
      expect(screen.getByAltText(/Preview of f2.jpg/)).toBeInTheDocument();
    });
  });

  it('shows error for invalid file type', async () => {
    const _user = userEvent.setup();
    render(
      <BrowserRouter>
        <AddByPhotoModal isOpen onClose={vi.fn()} />
      </BrowserRouter>
    );
    const input = screen.getByLabelText(/choose files/i);
    const badFile = new File(['bad'], 'bad.txt', { type: 'text/plain' });
    // Remove accept attribute in test environment so the testing library will allow
    // uploading a file with a non-matching MIME type. Browsers normally prevent
    // selecting disallowed types; here we want to exercise our validation logic.
    (input as HTMLInputElement).removeAttribute('accept');
    await _user.upload(input, badFile);
    await waitFor(() => {
      expect(
        screen.getByText(/Please select only image files/)
      ).toBeInTheDocument();
    });
  });

  it('shows error if camera permission denied (simulated)', async () => {
    // Simulate camera permission denied by dispatching an error event
    const _user = userEvent.setup();
    render(
      <BrowserRouter>
        <AddByPhotoModal isOpen onClose={vi.fn()} />
      </BrowserRouter>
    );
    const cameraInput = document.querySelector(
      'input[capture="environment"]'
    ) as HTMLInputElement;
    // Simulate error: no file selected by firing a change event with empty FileList
    const event = new Event('change', { bubbles: true });
    Object.defineProperty(cameraInput, 'files', { value: [], writable: false });
    cameraInput.dispatchEvent(event);
    await waitFor(() => {
      expect(
        screen.getByText(/Please select at least one file/)
      ).toBeInTheDocument();
    });
  });
});
