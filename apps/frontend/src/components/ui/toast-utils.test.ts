import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

describe('toast-utils', () => {
  beforeEach(() => {
    // Ensure we get a fresh module instance and deterministic time
    vi.resetModules();
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2025-01-01T00:00:00.000Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('addToast assigns createdAt when not provided', async () => {
    const mod = await import('./toast-utils');
    const toast = { id: 't1', message: 'hi', type: 'info' } as const;
    mod.addToast(toast as any);
    const toasts = mod.getToasts();
    expect(toasts).toHaveLength(1);
    expect(typeof toasts[0].createdAt).toBe('number');
    expect(toasts[0].createdAt).toBe(Date.now());
  });

  it('addToastIfNotExists prevents immediate duplicate within default window', async () => {
    const mod = await import('./toast-utils');
    const toast = { id: 't1', message: 'dup', type: 'error' } as any;
    mod.addToastIfNotExists(toast);
    mod.addToastIfNotExists({ id: 't2', message: 'dup', type: 'error' });
    const toasts = mod.getToasts();
    expect(toasts).toHaveLength(1);
    expect(toasts[0].id).toBe('t1');
  });

  it('addToastIfNotExists allows a new toast after dedup window elapses', async () => {
    const mod = await import('./toast-utils');
    const toast1 = { id: 't1', message: 'later', type: 'info' } as any;
    mod.addToastIfNotExists(toast1);

    // advance time past default 5s window
    vi.advanceTimersByTime(6000);

    mod.addToastIfNotExists({ id: 't2', message: 'later', type: 'info' });

    const toasts = mod.getToasts();
    expect(toasts).toHaveLength(2);
    expect(toasts.map((t) => t.id)).toEqual(['t1', 't2']);
  });

  it('addToastIfNotExists with dedupWindowMs=0 treats any match as duplicate', async () => {
    const mod = await import('./toast-utils');
    mod.addToastIfNotExists({ id: 't1', message: 'x', type: 'success' });
    mod.addToastIfNotExists({ id: 't2', message: 'x', type: 'success' }, 0);
    const toasts = mod.getToasts();
    expect(toasts).toHaveLength(1);
    expect(toasts[0].id).toBe('t1');
  });
});
