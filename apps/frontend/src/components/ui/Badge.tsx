import clsx from 'clsx';
import type { ReactNode } from 'react';

export type BadgeVariant = 'primary' | 'secondary' | 'success' | 'warning' | 'danger';

export interface BadgeProps {
  /**
   * Badge content
   */
  children: ReactNode;

  /**
   * Badge variant
   * @default 'secondary'
   */
  variant?: BadgeVariant;

  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Badge component for displaying labels and counts
 *
 * @example
 * ```tsx
 * <Badge variant="primary">New</Badge>
 * <Badge variant="secondary">3 meals</Badge>
 * ```
 */
export function Badge({
  children,
  variant = 'secondary',
  className = '',
}: BadgeProps) {
  const variantStyles = {
    primary: 'bg-primary-100 text-primary-800',
    secondary: 'bg-gray-100 text-gray-800',
    success: 'bg-green-100 text-green-800',
    warning: 'bg-yellow-100 text-yellow-800',
    danger: 'bg-red-100 text-red-800',
  };

  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        variantStyles[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
