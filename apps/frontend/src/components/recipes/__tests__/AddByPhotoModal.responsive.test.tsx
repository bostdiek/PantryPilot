import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../../hooks/useMediaQuery', () => ({
  useIsMobile: vi.fn(),
}));

import { useIsMobile } from '../../../hooks/useMediaQuery';
import { AddByPhotoModal } from '../../recipes/AddByPhotoModal';

const defaultProps = {
  isOpen: true,
  onClose: vi.fn(),
};

describe('AddByPhotoModal responsive layout', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('stacks buttons vertically on mobile', async () => {
    // @ts-expect-error mocked
    (useIsMobile as unknown as vi.Mock).mockReturnValue(true);

    render(
      <BrowserRouter>
        <AddByPhotoModal {...defaultProps} />
      </BrowserRouter>
    );

    const takePhoto = screen.getByRole('button', { name: /take photo/i });
    const chooseFiles = screen.getByRole('button', {
      name: /open file chooser/i,
    });

    expect(takePhoto).toBeInTheDocument();
    expect(chooseFiles).toBeInTheDocument();
  });

  it('places buttons side-by-side on desktop', () => {
    // @ts-expect-error mocked
    (useIsMobile as unknown as vi.Mock).mockReturnValue(false);

    render(
      <BrowserRouter>
        <AddByPhotoModal {...defaultProps} />
      </BrowserRouter>
    );

    const takePhoto = screen.getByRole('button', { name: /take photo/i });
    const chooseFiles = screen.getByRole('button', {
      name: /open file chooser/i,
    });

    expect(takePhoto).toBeInTheDocument();
    expect(chooseFiles).toBeInTheDocument();

    const parent = takePhoto.parentElement;
    expect(parent).toBe(chooseFiles.parentElement);
  });
});
