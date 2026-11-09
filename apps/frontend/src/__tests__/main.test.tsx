import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { render, replace } = vi.hoisted(() => ({
  render: vi.fn(),
  replace: vi.fn(),
}));
vi.mock('react-dom/client', () => ({
  createRoot: vi.fn(() => ({ render })),
}));
vi.mock('../App', () => ({ default: () => null }));

describe('production canonical origin', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    vi.stubEnv('VITE_CANONICAL_ORIGIN', 'https://smartmealplanner.app');
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it.each([
    'https://example.azurestaticapps.net',
    'https://www.smartmealplanner.app',
  ])(
    'redirects %s before rendering while preserving the full route',
    async (origin) => {
      vi.stubGlobal('window', {
        location: {
          origin,
          pathname: '/reset-password',
          search: '?token=example',
          hash: '#form',
          replace,
        },
      });
      await import('../main');
      expect(replace).toHaveBeenCalledExactlyOnceWith(
        'https://smartmealplanner.app/reset-password?token=example#form'
      );
      expect(render).not.toHaveBeenCalled();
    }
  );

  it.each([
    ['https://smartmealplanner.app', 'https://smartmealplanner.app'],
    ['http://localhost:5173', ''],
  ])('renders %s without a redirect', async (origin, canonical) => {
    vi.stubEnv('VITE_CANONICAL_ORIGIN', canonical);
    vi.stubGlobal('window', { location: { origin, replace } });
    await import('../main');
    expect(replace).not.toHaveBeenCalled();
    expect(render).toHaveBeenCalledOnce();
  });
});
