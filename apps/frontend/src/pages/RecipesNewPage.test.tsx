import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, test, vi } from 'vitest';
import RecipesNewPage from './RecipesNewPage';

// Mock SVG imports for Select icons
vi.mock('../components/ui/icons/chevron-up-down.svg?react', () => ({
  default: () => <div data-testid="mock-chevron-icon" />,
}));
vi.mock('../components/ui/icons/check.svg?react', () => ({
  default: () => <div data-testid="mock-check-icon" />,
}));
// Mock router navigation
const navigateMock = vi.fn();
vi.mock('react-router-dom', async () => ({
  ...(await vi.importActual('react-router-dom')),
  useNavigate: () => navigateMock,
}));

describe('RecipesNewPage', () => {
  test('renders form fields and buttons', () => {
    render(
      <MemoryRouter>
        <RecipesNewPage />
      </MemoryRouter>
    );

    // Text inputs by label
    expect(screen.getByLabelText(/recipe name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();

    // Category select by label
    expect(screen.getByLabelText(/category/i)).toBeInTheDocument();

    // Numeric inputs by label
    expect(screen.getByLabelText(/prep \(min\)/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/cook \(min\)/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/min servings/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/max servings/i)).toBeInTheDocument();
  });

  test('adds and removes ingredients dynamically', () => {
    render(
      <MemoryRouter>
        <RecipesNewPage />
      </MemoryRouter>
    );

    const addButton = screen.getByText(/add ingredient/i);
    fireEvent.click(addButton);
    expect(screen.getAllByLabelText(/ingredient/i)).toHaveLength(2);

    const removeButtons = screen.getAllByText(/remove/i);
    fireEvent.click(removeButtons[0]);
    expect(screen.getAllByLabelText(/ingredient/i)).toHaveLength(1);
  });

  test('adds and removes instruction steps dynamically', () => {
    render(
      <MemoryRouter>
        <RecipesNewPage />
      </MemoryRouter>
    );

    const addStep = screen.getByText(/add step/i);
    fireEvent.click(addStep);
    expect(screen.getAllByPlaceholderText(/step/i)).toHaveLength(2);

    const removeButtons = screen.getAllByText(/remove/i);
    // last remove for instructions
    fireEvent.click(removeButtons[removeButtons.length - 1]);
    expect(screen.getAllByPlaceholderText(/step/i)).toHaveLength(1);
  });

  test('cancel button navigates back', () => {
    render(
      <MemoryRouter>
        <RecipesNewPage />
      </MemoryRouter>
    );

    const cancel = screen.getByText(/cancel/i);
    fireEvent.click(cancel);
    expect(navigateMock).toHaveBeenCalledWith('/recipes');
  });

  test('submit navigates after save', () => {
    render(
      <MemoryRouter>
        <RecipesNewPage />
      </MemoryRouter>
    );

    const save = screen.getByText(/save recipe/i);
    fireEvent.click(save);
    expect(navigateMock).toHaveBeenCalledWith('/recipes');
  });
});
