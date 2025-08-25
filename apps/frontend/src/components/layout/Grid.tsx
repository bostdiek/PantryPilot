import type { ReactNode } from 'react';
import React from 'react';
import clsx from 'clsx';

/**
 * Grid component for responsive grid layouts
 */
export interface GridProps {
  /** Number of columns (Tailwind grid-cols-{n}) */
  columns?: number;
  /** Gap size (Tailwind gap-{n}) */
  gap?: number;
  children: ReactNode;
  className?: string;
}

export const Grid: React.FC<GridProps> = ({
  columns = 2,
  gap = 4,
  children,
  className = '',
}) => {
  const colsClass = `grid-cols-${columns}`;
  const gapClass = `gap-${gap}`;
  return (
    <div className={clsx('grid', colsClass, gapClass, className)}>
      {children}
    </div>
  );
};
