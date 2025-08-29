import clsx from 'clsx';
import type { HTMLAttributes, ReactNode } from 'react';
import { forwardRef } from 'react';

export type CardVariant = 'default' | 'outlined' | 'elevated';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /**
   * Card content
   */
  children: ReactNode;

  /**
   * Card variant
   * @default 'default'
   */
  variant?: CardVariant;

  /**
   * Card title
   */
  title?: string;

  /**
   * Header actions (e.g. buttons, menu)
   */
  headerActions?: ReactNode;

  /**
   * Footer content
   */
  footer?: ReactNode;

  /**
   * Removes padding from the card
   * @default false
   */
  noPadding?: boolean;

  /**
   * Makes the card take the full width of its container
   * @default false
   */
  fullWidth?: boolean;

  /**
   * Makes the card take the full height of its container
   * @default false
   */
  fullHeight?: boolean;

  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Card component for containing content in a bordered box
 *
 * @example
 * ```tsx
 * <Card title="Recipe Details">
 *   <p>This is the card content</p>
 * </Card>
 * ```
 */
export const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      children,
      variant = 'default',
      title,
      headerActions,
      footer,
      noPadding = false,
      fullWidth = false,
      fullHeight = false,
      className = '',
      onClick,
      ...props
    },
    ref
  ) => {
    // Variant styles with enhanced contrast and visual design
    const variantStyles = {
      default: 'bg-white border border-gray-200 hover:border-gray-300',
      outlined: 'bg-white border-2 border-gray-300 hover:border-primary-400',
      elevated:
        'bg-white border border-gray-200 shadow-card hover:shadow-card-hover',
    };

    // Size styles
    const sizeStyles = clsx(fullWidth && 'w-full', fullHeight && 'h-full');

    // Padding style
    const paddingStyle = noPadding ? '' : 'p-4';

    // Combined styles
    const combinedStyles = clsx(
      'rounded-lg overflow-hidden transition-all duration-200',
      variantStyles[variant],
      sizeStyles,
      paddingStyle,
      className
    );

    return (
      <div ref={ref} className={combinedStyles} onClick={onClick} {...props}>
        {(title || headerActions) && (
          <div className="flex items-center justify-between border-b border-gray-200 bg-gray-50 px-4 py-3">
            {title && (
              <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
            )}
            {headerActions && (
              <div className="flex items-center">{headerActions}</div>
            )}
          </div>
        )}

        <div className={paddingStyle}>{children}</div>

        {footer && (
          <div className="border-t border-gray-200 bg-gray-50 px-4 py-3">
            {footer}
          </div>
        )}
      </div>
    );
  }
);

Card.displayName = 'Card';
