---
description: "Create a new React component with TypeScript, proper hooks, and testing"
mode: "agent"
tools: ['changes', 'codebase', 'editFiles', 'extensions', 'fetch', 'findTestFiles', 'githubRepo', 'new', 'openSimpleBrowser', 'problems', 'runCommands', 'runNotebooks', 'runTasks', 'runTests', 'search', 'searchResults', 'terminalLastCommand', 'terminalSelection', 'testFailure', 'usages', 'vscodeAPI', 'context7', 'microsoft-docs', 'sequentialthinking']
---

# Create React Component

Generate a complete React component following PantryPilot frontend patterns and modern React 19+ best practices.

## Context

You are working in the PantryPilot frontend (`apps/frontend/`), which uses:

- **React**: 19.1.0+ with modern hooks and concurrent features
- **TypeScript**: 5.8.3+ with strict mode enabled
- **Vite**: 7.0.4+ for build tooling
- **Tailwind CSS**: 4.1.11+ for styling
- **Vitest**: 3.2.4+ for testing with React Testing Library

## Requirements

When creating a new React component, include:

1. **TypeScript Interface**: Proper prop types with strict typing
2. **React Hooks**: Modern patterns with useCallback, useMemo when appropriate
3. **Accessibility**: ARIA attributes and semantic HTML
4. **Styling**: Tailwind CSS classes with responsive design
5. **Error Handling**: Error boundaries and loading states
6. **Testing**: Comprehensive unit tests with Vitest and React Testing Library
7. **Documentation**: JSDoc comments and prop descriptions

## Template Structure

### 1. Component Interface (`types/`)

```typescript
/**
 * Props for the {ComponentName} component
 */
export interface {ComponentName}Props {
  /** Unique identifier for the component */
  id?: string;
  /** Additional CSS classes to apply */
  className?: string;
  /** Children to render inside the component */
  children?: React.ReactNode;
  /** Whether the component is disabled */
  disabled?: boolean;
  /** Loading state indicator */
  loading?: boolean;
  /** Error state with optional message */
  error?: string | null;
  /** Callback fired when interaction occurs */
  onAction?: (data: any) => void;
  /** Data to display in the component */
  data?: {ComponentName}Data | null;
}

/**
 * Data structure for {ComponentName}
 */
export interface {ComponentName}Data {
  id: number;
  name: string;
  description?: string;
  createdAt: string;
  updatedAt: string;
}

/**
 * State interface for {ComponentName}
 */
export interface {ComponentName}State {
  isLoading: boolean;
  error: string | null;
  data: {ComponentName}Data | null;
}
```

### 2. Component Implementation

````typescript
import React, { useCallback, useMemo, useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { {ComponentName}Props, {ComponentName}Data, {ComponentName}State } from './types';

/**
 * {ComponentName} component for displaying and managing {entity} data
 *
 * @example
 * ```tsx
 * <{ComponentName}
 *   data={entityData}
 *   onAction={handleAction}
 *   loading={isLoading}
 * />
 * ```
 */
export const {ComponentName}: React.FC<{ComponentName}Props> = ({
  id,
  className,
  children,
  disabled = false,
  loading = false,
  error = null,
  onAction,
  data,
  ...props
}) => {
  // Internal state management
  const [state, setState] = useState<{ComponentName}State>({
    isLoading: loading,
    error,
    data,
  });

  // Update state when props change
  useEffect(() => {
    setState(prev => ({
      ...prev,
      isLoading: loading,
      error,
      data,
    }));
  }, [loading, error, data]);

  // Memoized computed values
  const hasData = useMemo(() => state.data !== null, [state.data]);
  const showError = useMemo(() => !!state.error, [state.error]);
  const showLoading = useMemo(() => state.isLoading && !showError, [state.isLoading, showError]);

  // Event handlers
  const handleAction = useCallback((actionData: any) => {
    if (disabled || state.isLoading) return;

    onAction?.(actionData);
  }, [disabled, state.isLoading, onAction]);

  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleAction({ type: 'keyboard', key: event.key });
    }
  }, [handleAction]);

  // Render helpers
  const renderError = () => (
    <div
      className="rounded-md bg-red-50 p-4 border border-red-200"
      role="alert"
      aria-live="polite"
    >
      <div className="flex">
        <div className="flex-shrink-0">
          <svg
            className="h-5 w-5 text-red-400"
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <div className="ml-3">
          <h3 className="text-sm font-medium text-red-800">
            Error
          </h3>
          <div className="mt-2 text-sm text-red-700">
            {state.error}
          </div>
        </div>
      </div>
    </div>
  );

  const renderLoading = () => (
    <div
      className="flex items-center justify-center p-8"
      role="status"
      aria-live="polite"
      aria-label="Loading"
    >
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      <span className="ml-3 text-sm text-gray-600">Loading...</span>
    </div>
  );

  const renderContent = () => {
    if (!hasData) {
      return (
        <div className="text-center py-8">
          <p className="text-gray-500">No data available</p>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">
            {state.data?.name}
          </h3>
          <button
            type="button"
            onClick={() => handleAction({ type: 'edit', id: state.data?.id })}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            className={cn(
              "px-3 py-1 text-sm rounded-md transition-colors",
              "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2",
              disabled
                ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                : "bg-blue-600 text-white hover:bg-blue-700"
            )}
            aria-label={`Edit ${state.data?.name}`}
          >
            Edit
          </button>
        </div>

        {state.data?.description && (
          <p className="text-gray-600">{state.data.description}</p>
        )}

        <div className="text-xs text-gray-500 space-y-1">
          <p>Created: {new Date(state.data?.createdAt || '').toLocaleDateString()}</p>
          <p>Updated: {new Date(state.data?.updatedAt || '').toLocaleDateString()}</p>
        </div>

        {children}
      </div>
    );
  };

  return (
    <div
      id={id}
      className={cn(
        "bg-white rounded-lg border border-gray-200 shadow-sm",
        "transition-shadow duration-200",
        "hover:shadow-md focus-within:ring-2 focus-within:ring-blue-500",
        disabled && "opacity-50 cursor-not-allowed",
        className
      )}
      {...props}
    >
      <div className="p-6">
        {showError && renderError()}
        {showLoading && renderLoading()}
        {!showError && !showLoading && renderContent()}
      </div>
    </div>
  );
};

{ComponentName}.displayName = '{ComponentName}';

export default {ComponentName};
````

### 3. Custom Hook (Optional)

```typescript
import { useState, useEffect, useCallback } from 'react';
import { {ComponentName}Data, {ComponentName}State } from './types';

/**
 * Custom hook for managing {ComponentName} state and API interactions
 */
export const use{ComponentName} = (initialData?: {ComponentName}Data | null) => {
  const [state, setState] = useState<{ComponentName}State>({
    isLoading: false,
    error: null,
    data: initialData || null,
  });

  const fetchData = useCallback(async (id: number) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await fetch(`/api/v1/{entities}/${id}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch {entity}: ${response.statusText}`);
      }

      const data = await response.json();
      setState(prev => ({ ...prev, data, isLoading: false }));
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Unknown error',
        isLoading: false,
      }));
    }
  }, []);

  const updateData = useCallback(async (id: number, updates: Partial<{ComponentName}Data>) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await fetch(`/api/v1/{entities}/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });

      if (!response.ok) {
        throw new Error(`Failed to update {entity}: ${response.statusText}`);
      }

      const data = await response.json();
      setState(prev => ({ ...prev, data, isLoading: false }));
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Unknown error',
        isLoading: false,
      }));
    }
  }, []);

  const deleteData = useCallback(async (id: number) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await fetch(`/api/v1/{entities}/${id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`Failed to delete {entity}: ${response.statusText}`);
      }

      setState(prev => ({ ...prev, data: null, isLoading: false }));
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Unknown error',
        isLoading: false,
      }));
    }
  }, []);

  return {
    ...state,
    fetchData,
    updateData,
    deleteData,
  };
};
```

### 4. Component Tests

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { {ComponentName} } from './{ComponentName}';
import { {ComponentName}Props, {ComponentName}Data } from './types';

const mockData: {ComponentName}Data = {
  id: 1,
  name: 'Test {Entity}',
  description: 'Test description',
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
};

const defaultProps: {ComponentName}Props = {
  data: mockData,
  onAction: vi.fn(),
};

describe('{ComponentName}', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders with data correctly', () => {
      render(<{ComponentName} {...defaultProps} />);

      expect(screen.getByText('Test {Entity}')).toBeInTheDocument();
      expect(screen.getByText('Test description')).toBeInTheDocument();
    });

    it('renders loading state', () => {
      render(<{ComponentName} {...defaultProps} data={null} loading={true} />);

      expect(screen.getByRole('status')).toBeInTheDocument();
      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    it('renders error state', () => {
      const error = 'Something went wrong';
      render(<{ComponentName} {...defaultProps} error={error} />);

      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(error)).toBeInTheDocument();
    });

    it('renders no data state', () => {
      render(<{ComponentName} {...defaultProps} data={null} />);

      expect(screen.getByText('No data available')).toBeInTheDocument();
    });
  });

  describe('Interactions', () => {
    it('calls onAction when edit button is clicked', async () => {
      const user = userEvent.setup();
      const mockOnAction = vi.fn();

      render(<{ComponentName} {...defaultProps} onAction={mockOnAction} />);

      const editButton = screen.getByRole('button', { name: /edit/i });
      await user.click(editButton);

      expect(mockOnAction).toHaveBeenCalledWith({
        type: 'edit',
        id: mockData.id,
      });
    });

    it('calls onAction on keyboard interaction', async () => {
      const user = userEvent.setup();
      const mockOnAction = vi.fn();

      render(<{ComponentName} {...defaultProps} onAction={mockOnAction} />);

      const editButton = screen.getByRole('button', { name: /edit/i });
      editButton.focus();
      await user.keyboard('{Enter}');

      expect(mockOnAction).toHaveBeenCalledWith({
        type: 'keyboard',
        key: 'Enter',
      });
    });

    it('does not call onAction when disabled', async () => {
      const user = userEvent.setup();
      const mockOnAction = vi.fn();

      render(<{ComponentName} {...defaultProps} onAction={mockOnAction} disabled={true} />);

      const editButton = screen.getByRole('button', { name: /edit/i });
      await user.click(editButton);

      expect(mockOnAction).not.toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA attributes', () => {
      render(<{ComponentName} {...defaultProps} />);

      const editButton = screen.getByRole('button', { name: /edit/i });
      expect(editButton).toHaveAttribute('aria-label', `Edit ${mockData.name}`);
    });

    it('has proper loading state ARIA attributes', () => {
      render(<{ComponentName} {...defaultProps} data={null} loading={true} />);

      const loadingElement = screen.getByRole('status');
      expect(loadingElement).toHaveAttribute('aria-live', 'polite');
      expect(loadingElement).toHaveAttribute('aria-label', 'Loading');
    });

    it('has proper error state ARIA attributes', () => {
      render(<{ComponentName} {...defaultProps} error="Test error" />);

      const errorElement = screen.getByRole('alert');
      expect(errorElement).toHaveAttribute('aria-live', 'polite');
    });
  });

  describe('Styling', () => {
    it('applies custom className', () => {
      const customClass = 'custom-class';
      render(<{ComponentName} {...defaultProps} className={customClass} />);

      const component = screen.getByText('Test {Entity}').closest('div')?.closest('div');
      expect(component).toHaveClass(customClass);
    });

    it('applies disabled styling', () => {
      render(<{ComponentName} {...defaultProps} disabled={true} />);

      const editButton = screen.getByRole('button', { name: /edit/i });
      expect(editButton).toHaveClass('cursor-not-allowed');
      expect(editButton).toBeDisabled();
    });
  });
});
```

### 5. Storybook Stories (Optional)

```typescript
import type { Meta, StoryObj } from '@storybook/react';
import { {ComponentName} } from './{ComponentName}';
import { {ComponentName}Data } from './types';

const mockData: {ComponentName}Data = {
  id: 1,
  name: 'Sample {Entity}',
  description: 'This is a sample {entity} for demonstration purposes.',
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T12:00:00Z',
};

const meta: Meta<typeof {ComponentName}> = {
  title: 'Components/{ComponentName}',
  component: {ComponentName},
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    onAction: { action: 'onAction' },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    data: mockData,
  },
};

export const Loading: Story = {
  args: {
    loading: true,
    data: null,
  },
};

export const Error: Story = {
  args: {
    error: 'Failed to load {entity} data',
    data: null,
  },
};

export const NoData: Story = {
  args: {
    data: null,
  },
};

export const Disabled: Story = {
  args: {
    data: mockData,
    disabled: true,
  },
};
```

## Usage Instructions

1. **Specify the component and entity names** when using this prompt (e.g., "RecipeCard", "UserProfile")
2. **Replace placeholders** like `{ComponentName}`, `{entity}`, `{entities}` with your actual names
3. **Use Context7** to fetch the latest React 19+ documentation for specific patterns
4. **Import utilities** like `cn` from your utils library for class name handling
5. **Add to component index** for easy importing
6. **Run tests** to verify implementation: `npm run test -- {ComponentName}`

## Integration Steps

1. Define TypeScript interfaces for props and data
2. Implement the component with proper hooks and accessibility
3. Create custom hook for API interactions (if needed)
4. Write comprehensive tests with Vitest and React Testing Library
5. Add Storybook stories for documentation
6. Export from component index file
7. Update parent components to use the new component

Use Context7 to reference `/facebook/react` for the latest React patterns and `/microsoft/TypeScript` for TypeScript best practices when implementing your component.
