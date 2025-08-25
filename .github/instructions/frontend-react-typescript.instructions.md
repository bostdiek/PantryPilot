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
• Headless UI for accessible component foundations

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

### PantryPilot Domain Types

The application includes a set of domain-specific TypeScript types that should be used when working with data:

#### Recipe and Ingredient Types

```typescript
// Types for recipes and ingredients
type Recipe = {
  id: string;
  title: string;
  description: string;
  ingredients: Ingredient[];
  instructions: string[];
  cookTime: number; // in minutes
  prepTime: number; // in minutes
  servings: number;
  difficulty: "easy" | "medium" | "hard";
  tags: string[];
  imageUrl?: string; // optional
  ovenTemperatureF?: number; // optional
  createdAt: Date;
  updatedAt: Date;
};

type Ingredient = {
  id: string;
  name: string;
  quantity: number;
  unit: string;
};
```

#### Meal Planning Types

```typescript
type Meal = {
  dayOfWeek:
    | "Sunday"
    | "Monday"
    | "Tuesday"
    | "Wednesday"
    | "Thursday"
    | "Friday"
    | "Saturday";
  recipeId?: string;
  isLeftover: boolean;
  isEatingOut: boolean;
  notes?: string;
};

type MealPlan = {
  meals: Meal[];
};
```

#### User and Authentication Types

```typescript
interface AuthState {
  token: string | null;
  user: {
    id: string;
    username: string;
    email: string;
  } | null;
  login: (token: string, user: AuthState["user"]) => void;
  logout: () => void;
  setToken: (token: string | null) => void;
  setUser: (user: AuthState["user"]) => void;
}

type User = {
  userId: string;
  username: string;
  email: string;
};
```

#### Family Management Types

```typescript
type FamilyMember = {
  name: string;
  dietaryRestrictions: string[];
  allergies: string[];
  preferredCuisines: string[];
};

type Family = {
  members: FamilyMember[];
};
```

#### API Types

```typescript
// API Response Types
interface ApiResponse<T = unknown> {
  data?: T;
  message?: string;
  error?: string;
}

// Health Check Types
interface HealthCheckResponse {
  status: "healthy" | "unhealthy";
  message: string;
  timestamp?: string;
}

// Common API Error Type
interface ApiError {
  message: string;
  status?: number;
  code?: string;
}
```

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

### PantryPilot UI Component Library

The PantryPilot frontend includes a comprehensive set of UI components built on Headless UI and Tailwind CSS. These components should be used when building new pages and features.

#### Available UI Components

| Component        | Description                              | Props Interface   |
| ---------------- | ---------------------------------------- | ----------------- |
| `Button`         | Multi-variant button with loading states | `ButtonProps`     |
| `Card`           | Content container with various styles    | `CardProps`       |
| `Combobox`       | Searchable dropdown with autocomplete    | `ComboboxOption`  |
| `Container`      | Page container with size variants        | `ContainerProps`  |
| `Dialog`         | Modal dialog with focus management       | `DialogProps`     |
| `Disclosure`     | Expandable/collapsible content           | `DisclosureProps` |
| `Icon`           | SVG icon wrapper                         | N/A               |
| `Input`          | Form input with variants                 | `InputProps`      |
| `Select`         | Dropdown select field                    | `SelectOption`    |
| `Switch`         | Toggle switch control                    | `SwitchProps`     |
| `Tabs`           | Tabbed interface                         | `TabsProps`       |
| `LoadingSpinner` | Loading indicator                        | N/A               |
| `ErrorMessage`   | Error display component                  | N/A               |
| `EmptyState`     | Empty state placeholder                  | N/A               |

#### Layout Components

| Component | Description                                | Props Interface |
| --------- | ------------------------------------------ | --------------- |
| `Grid`    | CSS Grid layout wrapper                    | `GridProps`     |
| `Stack`   | Vertical or horizontal stack using Flexbox | `StackProps`    |

#### Available Icons

The application includes a set of SVG icons that can be imported and used with the `Icon` component:

- `CalendarIcon`
- `CheckIcon`
- `ChefHatIcon`
- `ChevronUpDownIcon`
- `KitchenIcon`
- `RestaurantIcon`

#### Component Usage Example

```tsx
import { Button, Card, Container, Input } from "../components/ui";

function RecipeForm() {
  return (
    <Container size="md">
      <Card variant="default" className="p-6">
        <h2 className="text-xl font-semibold mb-4">Create New Recipe</h2>
        <form>
          <div className="space-y-4">
            <Input
              label="Recipe Name"
              placeholder="Enter recipe name"
              type="text"
              required
            />

            <div className="flex justify-end">
              <Button variant="primary" type="submit">
                Save Recipe
              </Button>
            </div>
          </div>
        </form>
      </Card>
    </Container>
  );
}
```

### API Integration Patterns

#### API Client

PantryPilot uses a standardized API client for all backend interactions:

```typescript
// api/client.ts
import { useAuthStore } from "../stores/useAuthStore";
import type { ApiError, ApiResponse } from "../types/api";

// API configuration
const API_BASE_URL = getApiBaseUrl();

function getApiBaseUrl(): string {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  if (
    import.meta.env.MODE === "development" ||
    import.meta.env.MODE === "test"
  ) {
    return "http://localhost:8000";
  }
  throw new Error("VITE_API_URL must be set in production environments");
}

// API client with proper error handling
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private getAuthHeaders(): Record<string, string> {
    const token = useAuthStore.getState().token;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    // Ensure endpoint starts with /
    const normalizedEndpoint = endpoint.startsWith("/")
      ? endpoint
      : `/${endpoint}`;
    const url = `${this.baseUrl}${normalizedEndpoint}`;

    try {
      const headers = {
        "Content-Type": "application/json",
        ...this.getAuthHeaders(),
        ...(options?.headers || {}),
      };
      const resp = await fetch(url, {
        ...options,
        headers,
      });

      const body = (await resp.json()) as ApiResponse<T>;

      if (!resp.ok || body.error) {
        const apiError: ApiError = {
          message: body.error ?? `Request failed (${resp.status})`,
          status: resp.status,
        };
        throw apiError;
      }

      return body.data as T;
    } catch (err: unknown) {
      const apiError: ApiError =
        err instanceof Error
          ? { message: err.message }
          : { message: "Unknown error" };
      console.error(`API request failed: ${url}`, apiError);
      throw apiError;
    }
  }
}

// Export singleton instance
export const apiClient = new ApiClient(API_BASE_URL);
```

#### API Endpoints

The application has specific endpoint modules for different resources:

```typescript
// Example: api/endpoints/recipes.ts
import { apiClient } from "../client";
import type { Recipe } from "../types/Recipe";

export const recipesApi = {
  async getRecipes(): Promise<Recipe[]> {
    return apiClient.request<Recipe[]>("/api/v1/recipes");
  },

  async getRecipeById(id: string): Promise<Recipe> {
    return apiClient.request<Recipe>(`/api/v1/recipes/${id}`);
  },

  async createRecipe(
    recipe: Omit<Recipe, "id" | "createdAt" | "updatedAt">
  ): Promise<Recipe> {
    return apiClient.request<Recipe>("/api/v1/recipes", {
      method: "POST",
      body: JSON.stringify(recipe),
    });
  },

  async updateRecipe(id: string, recipe: Partial<Recipe>): Promise<Recipe> {
    return apiClient.request<Recipe>(`/api/v1/recipes/${id}`, {
      method: "PATCH",
      body: JSON.stringify(recipe),
    });
  },

  async deleteRecipe(id: string): Promise<void> {
    await apiClient.request(`/api/v1/recipes/${id}`, {
      method: "DELETE",
    });
  },
};
```

### Hooks and State Management

#### Zustand Store Pattern

PantryPilot uses Zustand for global state management. Create separate stores for different domains:

```typescript
// stores/useAuthStore.ts
import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { AuthState } from "../types/Auth";

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      login: (token, user) => set({ token, user }),
      logout: () => set({ token: null, user: null }),
      setToken: (token) => set({ token }),
      setUser: (user) => set({ user }),
    }),
    {
      name: "auth-storage", // unique name for localStorage
      partialize: (state) => ({ token: state.token, user: state.user }), // only persist token and user
    }
  )
);

// stores/useAppStore.ts
import { create } from "zustand";

interface AppState {
  currentPage: string;
  isMenuOpen: boolean;
  theme: "light" | "dark";

  setCurrentPage: (page: string) => void;
  toggleMenu: () => void;
  setTheme: (theme: "light" | "dark") => void;
}

export const useAppStore = create<AppState>((set) => ({
  currentPage: "home",
  isMenuOpen: false,
  theme: "light",

  setCurrentPage: (page) => set({ currentPage: page }),
  toggleMenu: () => set((state) => ({ isMenuOpen: !state.isMenuOpen })),
  setTheme: (theme) => set({ theme }),
}));
```

#### Custom Hooks

Create custom hooks for reusable logic:

```typescript
// Example: hooks/useApi.ts
import { useState, useCallback } from "react";
import type { ApiError } from "../types/api";

interface UseApiOptions<T> {
  initialData?: T;
  onSuccess?: (data: T) => void;
  onError?: (error: ApiError) => void;
}

export function useApi<T>(
  apiFunction: (...args: any[]) => Promise<T>,
  options: UseApiOptions<T> = {}
) {
  const [data, setData] = useState<T | null>(options.initialData || null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(false);

  const execute = useCallback(
    async (...args: any[]) => {
      try {
        setLoading(true);
        setError(null);
        const result = await apiFunction(...args);
        setData(result);
        options.onSuccess?.(result);
        return result;
      } catch (err) {
        const apiError = err as ApiError;
        setError(apiError);
        options.onError?.(apiError);
        throw apiError;
      } finally {
        setLoading(false);
      }
    },
    [apiFunction, options]
  );

  return {
    data,
    error,
    loading,
    execute,
  };
}
```

#### React Hooks Guidelines

• Follow React hooks rules (only call at top level, proper dependencies)
• Use `useState` for local component state management
• Implement `useEffect` with proper dependency arrays to avoid infinite loops
• Use `useCallback` and `useMemo` for performance optimization when needed
• Create custom hooks for reusable stateful logic
• Leverage context sparingly for deeply nested shared state

### Styling with Tailwind CSS

• Use Tailwind CSS 4.1.11+ utility classes for component styling
• Follow mobile-first responsive design with breakpoint prefixes
• Apply consistent spacing scale (`space-*`, `p-*`, `m-*`) throughout
• Use semantic color classes and CSS custom properties for theming
• Implement component variants with conditional class utilities
• Create reusable styling patterns with utility composition

### Testing Patterns with Vitest

#### Component Testing

```tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import { Button } from "./Button";

describe("Button", () => {
  it("renders correctly with default props", () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole("button")).toHaveTextContent("Click me");
  });

  it("calls onClick handler when clicked", async () => {
    const handleClick = vi.fn();
    const user = userEvent.setup();

    render(<Button onClick={handleClick}>Click me</Button>);
    await user.click(screen.getByRole("button"));

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it("displays loading state when loading prop is true", () => {
    render(<Button loading>Click me</Button>);
    expect(screen.getByRole("button")).toHaveAttribute("disabled");
    expect(document.querySelector("svg")).toBeInTheDocument(); // Loading spinner
  });
});
```

#### Store Testing

```tsx
import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { useAppStore } from "./useAppStore";

describe("useAppStore", () => {
  beforeEach(() => {
    // Reset the store before each test
    act(() => {
      useAppStore.setState({
        currentPage: "home",
        isMenuOpen: false,
        theme: "light",
      });
    });
  });

  it("should update current page", () => {
    const { result } = renderHook(() => useAppStore());

    act(() => {
      result.current.setCurrentPage("recipes");
    });

    expect(result.current.currentPage).toBe("recipes");
  });

  it("should toggle menu state", () => {
    const { result } = renderHook(() => useAppStore());

    act(() => {
      result.current.toggleMenu();
    });

    expect(result.current.isMenuOpen).toBe(true);

    act(() => {
      result.current.toggleMenu();
    });

    expect(result.current.isMenuOpen).toBe(false);
  });
});
```

#### API Testing

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiClient } from "./client";

// Mock fetch globally
beforeEach(() => {
  global.fetch = vi.fn();
});

describe("apiClient", () => {
  it("should handle successful requests", async () => {
    // Setup mock response
    const mockResponse = {
      ok: true,
      json: () =>
        Promise.resolve({ data: { id: 1, name: "Test" }, error: null }),
    };
    global.fetch = vi.fn().mockResolvedValue(mockResponse);

    // Make the request
    const result = await apiClient.request("/test");

    // Assertions
    expect(result).toEqual({ id: 1, name: "Test" });
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/test"),
      expect.objectContaining({
        headers: expect.objectContaining({
          "Content-Type": "application/json",
        }),
      })
    );
  });

  it("should handle API errors", async () => {
    // Setup mock error response
    const mockResponse = {
      ok: false,
      status: 404,
      json: () => Promise.resolve({ error: "Not found" }),
    };
    global.fetch = vi.fn().mockResolvedValue(mockResponse);

    // Make the request and expect it to throw
    await expect(apiClient.request("/test")).rejects.toMatchObject({
      message: "Not found",
      status: 404,
    });
  });
});
```

### Performance Optimization

#### Component Optimization

```tsx
import { memo, useMemo, useCallback } from "react";
import { Recipe } from "../types/Recipe";

interface RecipeListProps {
  recipes: Recipe[];
  onRecipeSelect: (id: string) => void;
}

// Use memo for components that render frequently with the same props
export const RecipeList = memo(
  ({ recipes, onRecipeSelect }: RecipeListProps) => {
    // Use useMemo for expensive computations
    const sortedRecipes = useMemo(() => {
      return [...recipes].sort((a, b) => a.title.localeCompare(b.title));
    }, [recipes]);

    // Use useCallback for event handlers that are passed to child components
    const handleRecipeClick = useCallback(
      (id: string) => {
        onRecipeSelect(id);
      },
      [onRecipeSelect]
    );

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {sortedRecipes.map((recipe) => (
          <div
            key={recipe.id}
            onClick={() => handleRecipeClick(recipe.id)}
            className="cursor-pointer"
          >
            <h3 className="font-medium">{recipe.title}</h3>
            <p className="text-sm text-gray-500">
              {recipe.prepTime + recipe.cookTime} mins • {recipe.difficulty}
            </p>
          </div>
        ))}
      </div>
    );
  }
);

RecipeList.displayName = "RecipeList";
```

#### Code Splitting with React.lazy

```tsx
import { lazy, Suspense } from "react";
import { LoadingSpinner } from "../components/ui";

// Lazy load page components
const RecipesPage = lazy(() => import("./RecipesPage"));
const MealPlanPage = lazy(() => import("./MealPlanPage"));
const RecipeDetailPage = lazy(() => import("./RecipeDetailPage"));

function AppRoutes() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-screen">
          <LoadingSpinner />
        </div>
      }
    >
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/recipes" element={<RecipesPage />} />
        <Route path="/recipes/:id" element={<RecipeDetailPage />} />
        <Route path="/meal-plan" element={<MealPlanPage />} />
      </Routes>
    </Suspense>
  );
}
```

### Page Structure and Layout

When building new pages, follow this consistent structure:

```tsx
import { Container, Card, Button } from "../components/ui";
import { Stack, Grid } from "../components/layout";
import { useApi } from "../hooks/useApi";
import { recipesApi } from "../api/endpoints/recipes";

function RecipesPage() {
  const {
    data: recipes,
    loading,
    error,
    execute: fetchRecipes,
  } = useApi(recipesApi.getRecipes);

  // Layout structure: Container -> Card -> Content
  return (
    <Container size="lg">
      <Stack spacing="lg">
        {/* Page header */}
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold">My Recipes</h1>
          <Button variant="primary">Add Recipe</Button>
        </div>

        {/* Main content */}
        <Card variant="default">
          {loading ? (
            <div className="py-12 flex justify-center">
              <LoadingSpinner />
            </div>
          ) : error ? (
            <div className="py-12 text-center">
              <p className="text-red-500">Failed to load recipes</p>
              <Button
                variant="secondary"
                className="mt-4"
                onClick={() => fetchRecipes()}
              >
                Retry
              </Button>
            </div>
          ) : recipes?.length === 0 ? (
            <EmptyState
              title="No recipes yet"
              description="Create your first recipe to get started"
              action={<Button variant="primary">Add Recipe</Button>}
            />
          ) : (
            <Grid columns={3} gap="md">
              {recipes?.map((recipe) => (
                <RecipeCard key={recipe.id} recipe={recipe} />
              ))}
            </Grid>
          )}
        </Card>
      </Stack>
    </Container>
  );
}

export default RecipesPage;
```

### Development Commands Reference

```bash
# Development server
npm run dev                 # Start Vite dev server

# Code quality
npm run lint                # ESLint checking
npm run type-check          # TypeScript checking
npm run format              # Prettier formatting

# Testing
npm run test                # Run Vitest
npm run test:ui             # Run with UI
npm run test:coverage       # Run with coverage

# Build
npm run build               # Production build
npm run preview             # Preview production build
```

### Component Development Guidelines

1. **Use Headless UI Components**: Leverage the built-in Headless UI components for accessible interactive elements.

2. **Component Naming**:

   - Use PascalCase for component names
   - Include descriptive suffixes (e.g., Button, Card, List)
   - Create separate files for large components

3. **Props Structure**:

   - Define clear prop interfaces with JSDoc comments
   - Use sensible defaults for optional props
   - Use properly typed event handlers

4. **Component Structure**:

   - Place helper functions within component or extract to custom hooks
   - Apply consistent Tailwind classes organization
   - Keep component files focused on a single responsibility

5. **Testing Focus**:

   - Test component behavior, not implementation details
   - Cover key user interactions and state changes
   - Test error and loading states

6. **Performance Considerations**:
   - Add memo() to components rendered frequently in lists
   - Use useCallback() for functions passed as props
   - Apply useMemo() for expensive calculations

By following these guidelines, you'll maintain consistency across the PantryPilot frontend and ensure high-quality, maintainable React components.
