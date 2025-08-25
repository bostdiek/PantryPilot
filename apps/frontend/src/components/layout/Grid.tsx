import clsx from 'clsx';
import type { ReactNode } from 'react';
import React from 'react';

// Predefined mapping for grid-cols-{n} classes to ensure Tailwind includes them
const GRID_COLS_CLASSES: Record<number, string> = {
  1: 'grid-cols-1',
  2: 'grid-cols-2',
  3: 'grid-cols-3',
  4: 'grid-cols-4',
  5: 'grid-cols-5',
  6: 'grid-cols-6',
  7: 'grid-cols-7',
  8: 'grid-cols-8',
  9: 'grid-cols-9',
  10: 'grid-cols-10',
  11: 'grid-cols-11',
  12: 'grid-cols-12',
};

// Predefined mapping for gap-{n} classes to ensure Tailwind includes them
const GAP_CLASSES: Record<number, string> = {
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
  // Use the columns class from the mapping, or fallback to grid-cols-2
  const colsClass = GRID_COLS_CLASSES[columns] || GRID_COLS_CLASSES[2];

  // Use the gap class from the mapping, or fallback to gap-4
  const gapClass = GAP_CLASSES[gap] || GAP_CLASSES[4];

  return (
    <div className={clsx('grid', colsClass, gapClass, className)}>
      {children}
    </div>
  );
};
