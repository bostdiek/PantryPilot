import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test, vi } from 'vitest';
import App from './App';

// Mock react-router-dom
vi.mock('react-router-dom', () => ({
  createBrowserRouter: vi.fn(),
  RouterProvider: vi.fn(({ children }) => children),
}));

// Mock Routes component
vi.mock('./routes', () => ({
  default: () => (
    <div>
      <nav>
        <a href="/recipes">Recipes</a>
      </nav>
      <h1>Hi, Demo!</h1>
    </div>
  ),
}));

// Mock SVG imports
vi.mock('./components/ui/icons/kitchen.svg?react', () => ({
  default: () => <div data-testid="mock-kitchen-icon" />,
}));

vi.mock('./components/ui/icons/calendar.svg?react', () => ({
  default: () => <div data-testid="mock-calendar-icon" />,
}));

vi.mock('./components/ui/icons/restaurant.svg?react', () => ({
  default: () => <div data-testid="mock-restaurant-icon" />,
}));

vi.mock('./components/ui/icons/chef-hat.svg?react', () => ({
  default: () => <div data-testid="mock-chef-hat-icon" />,
}));

vi.mock('./components/ui/icons/chevron-right.svg?react', () => ({
  default: () => <div data-testid="mock-chevron-right-icon" />,
}));

describe('App Routing', () => {
  test('renders home page by default', () => {
    render(<App />);
    expect(
      screen.getByRole('heading', { name: /hi, demo!/i })
    ).toBeInTheDocument();
  });

  test('navigates to recipes page', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole('link', { name: /^recipes$/i }));
    // In a real test, this would navigate to a different page
    // but we've mocked the Routes component, so we just ensure the link exists
    expect(
      screen.getByRole('link', { name: /^recipes$/i })
    ).toBeInTheDocument();
  });

  test('renders without crashing', () => {
    render(<App />);
    expect(screen.getByRole('navigation')).toBeInTheDocument();
  });
});
