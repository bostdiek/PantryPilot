import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Card } from './ui/Card';
import { Button } from './ui/Button';
import { Container } from './ui/Container';

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

/**
 * React Error Boundary component that catches JavaScript errors in component trees.
 * 
 * Features:
 * - Catches unhandled React component errors
 * - Shows user-friendly error message (no technical details)
 * - Provides reset functionality
 * - Optional error reporting callback
 * - Prevents app crashes from propagating to users
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log the error details for debugging (in development only)
    if (import.meta.env.MODE === 'development') {
      console.error('Error Boundary caught an error:', error);
      console.error('Error Info:', errorInfo);
    }

    // Call optional error reporting callback
    this.props.onError?.(error, errorInfo);

    // Store error info in state for potential debugging
    this.setState({
      error,
      errorInfo,
    });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default fallback UI
      return (
        <Container size="sm">
          <div className="flex min-h-screen flex-col items-center justify-center">
            <Card variant="default" className="w-full max-w-md p-6 text-center">
              <div className="mb-4">
                <h1 className="text-xl font-semibold text-gray-900">
                  Oops! Something went wrong
                </h1>
              </div>
              
              <div className="mb-6">
                <p className="text-gray-600">
                  We're sorry, but something unexpected happened. The page has been reset and you can try again.
                </p>
              </div>

              <div className="space-y-3">
                <Button
                  variant="primary"
                  onClick={this.handleReset}
                  className="w-full"
                >
                  Try Again
                </Button>
                
                <Button
                  variant="secondary"
                  onClick={() => {
                    window.location.href = '/';
                  }}
                  className="w-full"
                >
                  Go to Home Page
                </Button>
              </div>

              {/* Development-only error details */}
              {import.meta.env.MODE === 'development' && this.state.error && (
                <details className="mt-6 text-left">
                  <summary className="cursor-pointer text-sm text-gray-500 hover:text-gray-700">
                    Technical Details (Development Only)
                  </summary>
                  <div className="mt-2 p-3 bg-gray-50 rounded text-xs font-mono text-gray-700 overflow-auto">
                    <div className="mb-2">
                      <strong>Error:</strong> {this.state.error.message}
                    </div>
                    <div className="mb-2">
                      <strong>Stack:</strong>
                      <pre className="whitespace-pre-wrap">{this.state.error.stack}</pre>
                    </div>
                    {this.state.errorInfo && (
                      <div>
                        <strong>Component Stack:</strong>
                        <pre className="whitespace-pre-wrap">{this.state.errorInfo.componentStack}</pre>
                      </div>
                    )}
                  </div>
                </details>
              )}
            </Card>
          </div>
        </Container>
      );
    }

    return this.props.children;
  }
}

/**
 * Higher-order component to wrap any component with error boundary
 */
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, 'children'>
) {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;
  
  return WrappedComponent;
}