import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test } from 'vitest';
import App from './App';

describe('App Routing', () => {
  test('renders home page by default', () => {
    render(<App />);
    expect(
      screen.getByRole('heading', { name: /^home$/i })
    ).toBeInTheDocument();
  });

  test('navigates to recipes page', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole('link', { name: /^recipes$/i }));
    expect(
      screen.getByRole('heading', { name: /^recipes$/i })
    ).toBeInTheDocument();
  });

  test('renders without crashing', () => {
    render(<App />);
    expect(screen.getByRole('navigation')).toBeInTheDocument();
  });
});
