---
description: "React TypeScript frontend development guidelines for PantryPilot"
applyTo: "apps/frontend/**/*.{ts,tsx,js,jsx,css}"
---

# React TypeScript Frontend Development

Instructions for building high-quality React applications with TypeScript, modern hooks, and best practices following the official React documentation at [https://react.dev](https://react.dev/).

## Project Context

• React 19.1.0+ with modern hooks and concurrent features
• TypeScript 5.8.3+ with strict mode enabled
• Vite 7.0.4+ for build tooling and development server
• Tailwind CSS 4.1.11+ for utility-first styling
• Vitest 3.2.4+ for testing with React Testing Library
• ESLint 9.30.1+ and Prettier 3.6.2+ for code quality

## Development Standards

### React Components

• Use functional components with hooks as the primary pattern
• Write descriptive component names with PascalCase convention
• Implement proper TypeScript interfaces for all props and state
• Use composition over inheritance for component design
• Apply proper accessibility attributes (ARIA roles, semantic HTML)
• Include error boundaries and loading states for robust UX

### TypeScript Integration

• Enable strict mode in tsconfig.json for maximum type safety
• Use proper interface definitions with descriptive property names
• Leverage union types and generics for flexible component APIs
• Import types with `import type` syntax to optimize bundle size
• Include JSDoc comments for complex interfaces and functions
• Use `as const` assertions for literal types and readonly arrays

### Hooks and State Management

• Follow React hooks rules (only call at top level, proper dependencies)
• Use `useState` for local component state management
• Implement `useEffect` with proper dependency arrays to avoid infinite loops
• Use `useCallback` and `useMemo` for performance optimization when needed
• Create custom hooks for reusable stateful logic
• Leverage `useContext` for sharing state across component trees

### Styling with Tailwind CSS

• Use Tailwind CSS 4.1.11+ utility classes for component styling
• Follow mobile-first responsive design with breakpoint prefixes
• Apply consistent spacing scale (`space-*`, `p-*`, `m-*`) throughout
• Use semantic color classes and CSS custom properties for theming
• Implement component variants with conditional class utilities
• Create reusable styling patterns with utility composition

### Performance Optimization

• Use `React.memo` for component memoization when appropriate
• Implement code splitting with `React.lazy` and `Suspense` components
• Use `useMemo` and `useCallback` judiciously to prevent unnecessary renders
• Optimize bundle size with dynamic imports and tree shaking
• Profile components with React DevTools to identify bottlenecks
• Implement virtual scrolling for large data sets

### Testing

• Write unit tests using Vitest and React Testing Library
• Test component behavior rather than implementation details
• Mock external dependencies and API calls appropriately
• Implement integration tests for complex component interactions
• Test accessibility features and keyboard navigation
• Use descriptive test names that explain the expected behavior

### Code Quality and Standards

• Follow ESLint rules and Prettier formatting consistently
• Use meaningful variable and function names with clear intent
• Keep components small and focused on single responsibilities
• Implement proper error handling with try-catch blocks
• Document complex logic with clear comments explaining why
• Use consistent file and folder naming conventions

### Context7 Integration

• Use Context7 MCP server to fetch latest React documentation: `/facebook/react`
• Reference TypeScript best practices from official docs: `/microsoft/TypeScript`
• Leverage Tailwind CSS patterns and utilities: `/tailwindlabs/tailwindcss`
• Follow Vite configuration and optimization guides: `/vitejs/vite`

## State Management and Hooks

### React 19+ Modern Patterns

#### Component Definition with TypeScript

```tsx
import { useState, useCallback } from "react";

interface ItemProps {
  id: number;
  title: string;
  description?: string;
  onUpdate: (id: number, data: Partial<ItemData>) => void;
}

// Use function declarations for better debugging
function Item({ id, title, description, onUpdate }: ItemProps) {
  const [isEditing, setIsEditing] = useState(false);

  const handleUpdate = useCallback(
    (newData: Partial<ItemData>) => {
      onUpdate(id, newData);
    },
    [id, onUpdate]
  );

  return (
    <div className="p-4 border rounded-lg shadow-sm">
      <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
      {description && (
        <p className="mt-2 text-sm text-gray-600">{description}</p>
      )}
    </div>
  );
}

export default Item;
```

#### Custom Hooks Pattern

```tsx
import { useState, useEffect, useCallback } from "react";
import { apiClient } from "../api";

interface UseApiOptions<T> {
  initialData?: T;
  immediate?: boolean;
}

function useApi<T>(apiCall: () => Promise<T>, options: UseApiOptions<T> = {}) {
  const [data, setData] = useState<T | null>(options.initialData ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const execute = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await apiCall();
      setData(result);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Unknown error");
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  useEffect(() => {
    if (options.immediate) {
      execute();
    }
  }, [execute, options.immediate]);

  return { data, loading, error, execute };
}

export default useApi;
```

### TypeScript Best Practices

#### Strict Type Definitions

```tsx
// Define precise types for API responses
interface ApiResponse<T> {
  data: T;
  message: string;
  success: boolean;
}

interface User {
  id: number;
  email: string;
  name: string;
  createdAt: string;
}

// Use union types for component variants
type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  disabled?: boolean;
  loading?: boolean;
  children: React.ReactNode;
  onClick?: () => void;
}
```

#### Event Handlers

```tsx
import { ChangeEvent, FormEvent, KeyboardEvent } from "react";

function ContactForm() {
  const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    const { name, value } = event.target;
    // Handle input change
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    // Handle form submission
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      // Handle enter key
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        name="email"
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
      />
    </form>
  );
}
```

### Tailwind CSS Patterns

#### Component Styling

```tsx
// Use Tailwind's utility classes for consistent design
function Card({ children, variant = "default" }: CardProps) {
  const baseClasses = "rounded-lg shadow-sm border";
  const variantClasses = {
    default: "bg-white border-gray-200",
    primary: "bg-blue-50 border-blue-200",
    danger: "bg-red-50 border-red-200",
  };

  return (
    <div className={`${baseClasses} ${variantClasses[variant]} p-6`}>
      {children}
    </div>
  );
}

// Responsive design patterns
function ResponsiveGrid({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {children}
    </div>
  );
}
```

#### Design System Consistency

```tsx
// Define consistent spacing and typography
const spacing = {
  xs: "p-2",
  sm: "p-3",
  md: "p-4",
  lg: "p-6",
  xl: "p-8",
} as const;

const typography = {
  h1: "text-3xl font-bold text-gray-900",
  h2: "text-2xl font-semibold text-gray-900",
  h3: "text-lg font-medium text-gray-900",
  body: "text-base text-gray-700",
  caption: "text-sm text-gray-500",
} as const;
```

### API Integration Patterns

#### API Client Setup

```tsx
// api/client.ts
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export class ApiClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;

    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  // Convenience methods
  get<T>(endpoint: string) {
    return this.request<T>(endpoint, { method: "GET" });
  }

  post<T>(endpoint: string, data: unknown) {
    return this.request<T>(endpoint, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }
}

export const apiClient = new ApiClient();
```

#### Service Layer Pattern

```tsx
// api/services/userService.ts
import { apiClient } from "../client";
import type { User, CreateUserRequest, UpdateUserRequest } from "../types";

export const userService = {
  async getUsers(): Promise<User[]> {
    return apiClient.get<User[]>("/api/v1/users");
  },

  async createUser(userData: CreateUserRequest): Promise<User> {
    return apiClient.post<User>("/api/v1/users", userData);
  },

  async updateUser(id: number, userData: UpdateUserRequest): Promise<User> {
    return apiClient.request<User>(`/api/v1/users/${id}`, {
      method: "PATCH",
      body: JSON.stringify(userData),
    });
  },
};
```

### Testing Patterns with Vitest

#### Component Testing

```tsx
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import ContactForm from "./ContactForm";

describe("ContactForm", () => {
  it("should submit form with valid data", async () => {
    const mockOnSubmit = vi.fn();
    const user = userEvent.setup();

    render(<ContactForm onSubmit={mockOnSubmit} />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Message"), "Hello world");
    await user.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        email: "test@example.com",
        message: "Hello world",
      });
    });
  });

  it("should display validation errors", async () => {
    render(<ContactForm onSubmit={vi.fn()} />);

    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(screen.getByText("Email is required")).toBeInTheDocument();
  });
});
```

#### Hook Testing

```tsx
import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import useApi from "./useApi";

describe("useApi", () => {
  it("should handle successful API call", async () => {
    const mockApiCall = vi.fn().mockResolvedValue({ data: "test" });

    const { result } = renderHook(() => useApi(mockApiCall));

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.data).toEqual({ data: "test" });
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });
});
```

### Performance Optimization

#### Memo and Callback Optimization

```tsx
import { memo, useMemo, useCallback } from "react";

interface ExpensiveListProps {
  items: Item[];
  onItemClick: (id: number) => void;
}

const ExpensiveList = memo(({ items, onItemClick }: ExpensiveListProps) => {
  const sortedItems = useMemo(() => {
    return items.sort((a, b) => a.name.localeCompare(b.name));
  }, [items]);

  const handleItemClick = useCallback(
    (id: number) => {
      onItemClick(id);
    },
    [onItemClick]
  );

  return (
    <ul>
      {sortedItems.map((item) => (
        <ExpensiveListItem
          key={item.id}
          item={item}
          onClick={handleItemClick}
        />
      ))}
    </ul>
  );
});

ExpensiveList.displayName = "ExpensiveList";
```

#### Lazy Loading

```tsx
import { lazy, Suspense } from "react";

// Lazy load heavy components
const Dashboard = lazy(() => import("./Dashboard"));
const Reports = lazy(() => import("./Reports"));

function App() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      }
    >
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/reports" element={<Reports />} />
      </Routes>
    </Suspense>
  );
}
```

### Context7 Integration

When encountering React questions or needing examples:

- Reference `/reactjs/react.dev` for official React 19+ documentation
- Use Context7 to fetch current best practices for:
  - Modern hook patterns
  - TypeScript integration
  - Performance optimization
  - Testing strategies

### Environment Configuration

#### Vite Environment Variables

```typescript
// types/env.d.ts
interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_APP_NAME: string;
  readonly VITE_DEBUG: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// Usage
const apiUrl = import.meta.env.VITE_API_URL;
const isDebug = import.meta.env.VITE_DEBUG === "true";
```

### Development Commands Reference

```bash
# Development server
npm run dev                 # Start Vite dev server

# Code quality
npm run lint               # ESLint checking
npm run type-check         # TypeScript checking
npm run format             # Prettier formatting

# Testing
npm run test               # Run Vitest
npm run test:ui            # Run with UI
npm run test:coverage      # Run with coverage

# Build
npm run build              # Production build
npm run preview            # Preview production build
```

### Accessibility Best Practices

```tsx
// Semantic HTML and ARIA
function Modal({ title, children, onClose }: ModalProps) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
        <h2 id="modal-title" className="text-lg font-semibold mb-4">
          {title}
        </h2>
        {children}
        <button
          onClick={onClose}
          aria-label="Close modal"
          className="mt-4 px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
        >
          Close
        </button>
      </div>
    </div>
  );
}
```

Always prioritize type safety, component reusability, and modern React patterns. Use Context7 to reference the latest React documentation when implementing new features or optimizations.
