import clsx from 'clsx';
import type { ReactNode } from 'react';
import React from 'react';

/**
 * Stack component for vertical or horizontal stacking of children
 */
export interface StackProps {
  /** Direction of stacking: 'vertical' (column) or 'horizontal' (row) */
  direction?: 'vertical' | 'horizontal';
  /** Gap size between items (Tailwind gap-{n}) */
  gap?: number;
  children: ReactNode;
  className?: string;
}

export const Stack: React.FC<StackProps> = ({
  direction = 'vertical',
  gap = 4,
  children,
  className = '',
}) => {
  const dirClass = direction === 'vertical' ? 'flex-col' : 'flex-row';

  // Predefined gap classes to ensure Tailwind includes them
  const gapClasses = {
    0: 'gap-0',
    1: 'gap-1',
    2: 'gap-2',
    3: 'gap-3',
    4: 'gap-4',
    5: 'gap-5',
    6: 'gap-6',
    7: 'gap-7',
    8: 'gap-8',
    9: 'gap-9',
    10: 'gap-10',
    11: 'gap-11',
    12: 'gap-12',
  };

  // Use the gap class from the mapping, or fallback to gap-4
  const gapClass = gapClasses[gap as keyof typeof gapClasses] || gapClasses[4];

  return (
    <div className={clsx('flex', dirClass, gapClass, className)}>
      {children}
    </div>
  );
};
