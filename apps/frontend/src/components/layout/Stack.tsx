import type { ReactNode } from 'react';
import React from 'react';
import clsx from 'clsx';

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
  const gapClass = `gap-${gap}`;
  return (
    <div className={clsx('flex', dirClass, gapClass, className)}>
      {children}
    </div>
  );
};
