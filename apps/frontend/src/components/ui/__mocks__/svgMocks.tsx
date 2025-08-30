// Mock for testing
import type { SVGProps } from 'react';
import * as React from 'react';
import { vi } from 'vitest';

// Mock SVG imports for tests
vi.mock('./icons/check.svg?react', () => ({
  default: (props: SVGProps<SVGSVGElement>) =>
    React.createElement('svg', {
      ...props,
      'data-testid': 'check-icon',
    }),
}));

export { default as mockCheckIcon } from './icons/check.svg?react';
