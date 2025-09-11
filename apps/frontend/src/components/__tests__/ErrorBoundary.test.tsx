import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import userEvent from '@testing-library/user-event';
import { ErrorBoundary, withErrorBoundary } from '../ErrorBoundary';

// Test component that throws an error
const ThrowingComponent: React.FC<{ shouldThrow?: boolean }> = ({ shouldThrow = true }) => {
  if (shouldThrow) {
    throw new Error('Test error message');
  }
  return <div>Normal component</div>;
};

// Test component that renders children normally
const NormalComponent: React.FC = () => {
  return <div>This component works fine</div>;
};

describe('ErrorBoundary', () => {
  // Mock console.error to avoid noise in test output
  const originalConsoleError = console.error;
  beforeEach(() => {
    console.error = vi.fn();
  });

  afterEach(() => {
    console.error = originalConsoleError;
  });

  it('renders children when there is no error', () => {
    render(
      <ErrorBoundary>
        <NormalComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText('This component works fine')).toBeInTheDocument();
  });

  it('renders error UI when child component throws', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText('Oops! Something went wrong')).toBeInTheDocument();
    expect(screen.getByText(/We're sorry, but something unexpected happened/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Try Again' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Go to Home Page' })).toBeInTheDocument();
  });

  it('renders custom fallback when provided', () => {
    const customFallback = <div>Custom error message</div>;
    
    render(
      <ErrorBoundary fallback={customFallback}>
        <ThrowingComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom error message')).toBeInTheDocument();
    expect(screen.queryByText('Oops! Something went wrong')).not.toBeInTheDocument();
  });

  it('calls onError callback when error occurs', () => {
    const onError = vi.fn();
    
    render(
      <ErrorBoundary onError={onError}>
        <ThrowingComponent />
      </ErrorBoundary>
    );

    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({
        componentStack: expect.any(String),
      })
    );
  });

  it('resets error state when Try Again is clicked', async () => {
    const user = userEvent.setup();
    
    // Simple component that throws initially then recovers
    let shouldThrow = true;
    const ToggleComponent: React.FC = () => {
      if (shouldThrow) {
        throw new Error('Test error');
      }
      return <div>Component recovered</div>;
    };

    const { rerender } = render(
      <ErrorBoundary>
        <ToggleComponent />
      </ErrorBoundary>
    );

    // Error UI should be shown
    expect(screen.getByText('Oops! Something went wrong')).toBeInTheDocument();

    // Stop throwing error
    shouldThrow = false;

    // Click Try Again
    await user.click(screen.getByRole('button', { name: 'Try Again' }));

    // Re-render with the non-throwing component
    rerender(
      <ErrorBoundary>
        <ToggleComponent />
      </ErrorBoundary>
    );

    // Component should render normally now
    expect(screen.getByText('Component recovered')).toBeInTheDocument();
  });

  it('shows technical details in development mode', () => {
    // Mock import.meta.env.MODE
    const originalMode = import.meta.env.MODE;
    import.meta.env.MODE = 'development';

    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText('Technical Details (Development Only)')).toBeInTheDocument();

    // Restore original mode
    import.meta.env.MODE = originalMode;
  });

  it('hides technical details in production mode', () => {
    // Mock import.meta.env.MODE
    const originalMode = import.meta.env.MODE;
    import.meta.env.MODE = 'production';

    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );

    expect(screen.queryByText('Technical Details (Development Only)')).not.toBeInTheDocument();

    // Restore original mode
    import.meta.env.MODE = originalMode;
  });

  it('navigates to home when Go to Home Page is clicked', async () => {
    const user = userEvent.setup();
    
    // Mock window.location.href
    const originalLocation = window.location;
    delete (window as any).location;
    window.location = { ...originalLocation, href: '' };

    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );

    await user.click(screen.getByRole('button', { name: 'Go to Home Page' }));

    expect(window.location.href).toBe('/');

    // Restore original location
    window.location = originalLocation;
  });
});

describe('withErrorBoundary HOC', () => {
  it('wraps component with error boundary', () => {
    const WrappedComponent = withErrorBoundary(NormalComponent);
    
    render(<WrappedComponent />);

    expect(screen.getByText('This component works fine')).toBeInTheDocument();
  });

  it('passes error boundary props to wrapper', () => {
    const onError = vi.fn();
    
    const WrappedComponent = withErrorBoundary(ThrowingComponent, { onError });
    
    render(<WrappedComponent />);

    expect(onError).toHaveBeenCalledTimes(1);
  });

  it('sets correct display name', () => {
    const TestComponent: React.FC = () => <div>test</div>;
    TestComponent.displayName = 'TestComponent';
    
    const WrappedComponent = withErrorBoundary(TestComponent);
    
    expect(WrappedComponent.displayName).toBe('withErrorBoundary(TestComponent)');
  });
});