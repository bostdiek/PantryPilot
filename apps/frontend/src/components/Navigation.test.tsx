import { describe, expect, test } from 'vitest';

import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Navigation from './Navigation';

describe('Navigation', () => {
  test('renders all navigation links', () => {
    render(
      <MemoryRouter>
        {' '}
        <Navigation />{' '}
      </MemoryRouter>
    );

    expect(screen.getByRole('link', { name: /^home$/i })).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /^recipes$/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /add recipe/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /meal plan/i })
    ).toBeInTheDocument();
  });
});
