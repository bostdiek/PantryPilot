import * as TestingLibrary from '@testing-library/react';
import * as React from 'react';
import { vi } from 'vitest';

// Setup for Toast tests
// This file should be imported by test files that need Toast components

// Mock useToast hook
vi.mock('../useToast', () => ({
  useToast: () => ({
    toastList: [],
    showToast: vi.fn(),
    removeToast: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  }),
}));

// Re-export testing utilities with our custom render
// eslint-disable-next-line react-refresh/only-export-components
export * from '@testing-library/react';

// Override render method to include providers if needed
export const render = (ui: React.ReactElement) => {
  return TestingLibrary.render(ui);
};
