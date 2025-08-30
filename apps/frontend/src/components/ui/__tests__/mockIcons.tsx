import React from 'react';
import { vi } from 'vitest';

// Mock SVGs for tests
vi.mock('../icons/check.svg?react', () => ({
  default: (props: React.SVGProps<SVGSVGElement>) =>
    React.createElement('svg', { ...props, 'data-testid': 'check-icon' }),
}));

// Re-export the mocked icon
export { default as CheckIcon } from '../icons/check.svg?react';
