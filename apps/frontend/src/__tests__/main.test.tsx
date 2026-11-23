import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { render, replace } = vi.hoisted(() => ({
  render: vi.fn(),
  replace: vi.fn(),
}));
vi.mock('react-dom/client', () => ({
  createRoot: vi.fn(() => ({ render })),
}));
vi.mock('../App', () => ({ default: () => null }));

describe('canonical hosting origin', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it.each([
    ['https://example.azurestaticapps.net', 'https://dev.smartmealplanner.app'],
    ['https://smartmealplanner.app', 'https://dev.smartmealplanner.app'],
    ['https://www.smartmealplanner.app', 'https://dev.smartmealplanner.app'],
    ['https://example.azurestaticapps.net', 'https://smartmealplanner.app'],
    ['https://www.smartmealplanner.app', 'https://smartmealplanner.app'],
  ])(
    'redirects %s to %s before rendering and preserves the full route',
    async (origin, canonical) => {
      vi.stubEnv('VITE_CANONICAL_ORIGIN', canonical);
      vi.stubGlobal('window', {
        location: {
          origin,
          pathname: '/reset-password',
          search: '?token=a%2Bb&next=%2Frecipes',
          hash: '#form',
          replace,
        },
      });
      await import('../main');
      expect(replace).toHaveBeenCalledExactlyOnceWith(
        `${canonical}/reset-password?token=a%2Bb&next=%2Frecipes#form`
      );
      expect(render).not.toHaveBeenCalled();
    }
  );

  it.each([
    ['https://smartmealplanner.app', 'https://smartmealplanner.app'],
    ['https://dev.smartmealplanner.app', 'https://dev.smartmealplanner.app'],
    ['http://localhost:5173', ''],
    ['https://smartmealplanner.app', ''],
  ])('renders %s with canonical value %s', async (origin, canonical) => {
    vi.stubEnv('VITE_CANONICAL_ORIGIN', canonical);
    vi.stubGlobal('window', { location: { origin, replace } });
    await import('../main');
    expect(replace).not.toHaveBeenCalled();
    expect(render).toHaveBeenCalledOnce();
  });
});
