import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { resetToastMock } from '../../../__mocks__/useToast';
import { Toast } from '../Toast';
import { ToastContainer } from '../ToastContainer';
import { useToast } from '../useToast';

// Mock the useToast hook
vi.mock('../useToast');

// Mock the icon module used in Toast component
vi.mock('../icons/check.svg?react', () => ({
  default: vi.fn(() => null),
}));

describe('Toast', () => {
  beforeEach(() => {
    resetToastMock();
  });

  it('renders with the correct message', () => {
    render(
      <Toast
        message="Test message"
        type="success"
        testId="test-toast"
        onClose={() => {}}
      />
    );

    expect(screen.getByText('Test message')).toBeInTheDocument();
  });

  it('renders with correct type styles', () => {
    render(
      <Toast
        message="Test message"
        type="error"
        testId="test-toast"
        onClose={() => {}}
      />
    );

    const toastElement = screen.getByTestId('test-toast');
    expect(toastElement).toHaveClass('bg-red-50');
  });

  it('includes a dismiss button', () => {
    const onClose = vi.fn();

    render(
      <Toast
        message="Test message"
        type="info"
        testId="test-toast"
        onClose={onClose}
        duration={100} // Short duration for testing
      />
    );

    // Simply check that the button exists
    const closeButton = screen.getByTestId('test-toast-dismiss-button');
    expect(closeButton).toBeInTheDocument();
  });
});

describe('Toast Integration', () => {
  beforeEach(() => {
    resetToastMock();
  });

  it('renders toast container with toasts', () => {
    // Setup mock to return test toasts
    vi.mocked(useToast).mockImplementation(() => ({
      toastList: [
        {
          id: 'toast-success-test',
          message: 'Success message',
          type: 'success',
        },
        { id: 'toast-error-test', message: 'Error message', type: 'error' },
        { id: 'toast-info-test', message: 'Info message', type: 'info' },
      ],
      removeToast: vi.fn(),
      success: vi.fn(),
      error: vi.fn(),
      info: vi.fn(),
      showToast: vi.fn(),
    }));

    render(<ToastContainer />);

    // We're using the mock that returns three toasts
    expect(screen.getByText('Success message')).toBeInTheDocument();
    expect(screen.getByText('Error message')).toBeInTheDocument();
    expect(screen.getByText('Info message')).toBeInTheDocument();
  });
});
