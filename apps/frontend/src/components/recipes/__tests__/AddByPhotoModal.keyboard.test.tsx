import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '../../../stores/useAuthStore';
import { useRecipeStore } from '../../../stores/useRecipeStore';
import { AddByPhotoModal } from '../../recipes/AddByPhotoModal';

// Mock useIsMobile to a static desktop layout for this keyboard test
vi.mock('../../../hooks/useMediaQuery', () => ({ useIsMobile: () => false }));

// Mock navigate
const mockOnClose = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({
    token: 't',
    user: { id: '1', username: 'a', email: 'a@a.com' },
  });
  useRecipeStore.setState({ formSuggestion: null, isAISuggestion: false });
});

describe('AddByPhotoModal keyboard navigation', () => {
  it('moves focus between thumbnails with arrow keys', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <AddByPhotoModal isOpen onClose={mockOnClose} />
      </BrowserRouter>
    );

    // Add two files by simulating input change
    const input = document.querySelector(
      'input[type=file]'
    ) as HTMLInputElement;
    const file1 = new File(['a'], 'a.jpg', { type: 'image/jpeg' });
    const file2 = new File(['b'], 'b.jpg', { type: 'image/jpeg' });

    await user.upload(input, [file1, file2]);

    // Wait for thumbnails to appear
    const thumbButtons = await screen.findAllByRole('button', {
      name: /Preview/i,
    });
    expect(thumbButtons.length).toBeGreaterThanOrEqual(2);

    // Focus first thumbnail and press ArrowRight to move to second
    thumbButtons[0].focus();
    await user.keyboard('{ArrowRight}');

    // Now second should be focused
    expect(document.activeElement).toBe(thumbButtons[1]);
  });
});
