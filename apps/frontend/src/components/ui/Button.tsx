import { Button as HeadlessButton } from '@headlessui/react';
import clsx from 'clsx';
import type { ReactNode } from 'react';
import React, { forwardRef } from 'react';
import { Icon } from './Icon';

export type ButtonVariant =
  | 'primary'
  | 'secondary'
  | 'danger'
  | 'outline'
  | 'ghost';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps {
  /**
   * Button content
   */
  children: ReactNode;

  /**
   * Button variant
   * @default 'primary'
   */
  variant?: ButtonVariant;

  /**
   * Button size
   * @default 'md'
   */
  size?: ButtonSize;

  /**
   * Makes the button take the full width of its container
   * @default false
   */
  fullWidth?: boolean;

  /**
   * Disables the button
   * @default false
   */
  disabled?: boolean;

  /**
   * Shows a loading spinner
   * @default false
   */
  loading?: boolean;

  /**
   * Left icon path (from our icons directory)
   * @deprecated Use leftIconSvg instead
   */
  leftIcon?: string;

  /**
   * Right icon path (from our icons directory)
   * @deprecated Use rightIconSvg instead
   */
  rightIcon?: string;

  /**
   * Left icon SVG component
   */
  leftIconSvg?: React.ComponentType<React.SVGProps<SVGSVGElement>>;

  /**
   * Right icon SVG component
   */
  rightIconSvg?: React.ComponentType<React.SVGProps<SVGSVGElement>>;

  /**
   * Additional CSS classes
   */
  className?: string;

  /**
   * Click handler
   */
  onClick?: () => void;

  /**
   * Button type
   * @default 'button'
   */
  type?: 'button' | 'submit' | 'reset';

  /**
   * Native title attribute (tooltip)
   */
  title?: string;
}

/**
 * Button component built with Headless UI and Tailwind CSS
 *
 * @example
 * ```tsx
 * <Button variant="primary" size="md" onClick={() => console.log('Clicked!')}>
 *   Click me
 * </Button>
 * ```
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = 'primary',
      size = 'md',
      fullWidth = false,
      disabled = false,
      loading = false,
      leftIcon,
      rightIcon,
      leftIconSvg,
      rightIconSvg,
      className = '',
      onClick,
      type = 'button',
      ...props
    },
    ref
  ) => {
    // Base styles with improved transitions and focus states
    const baseStyles =
      'inline-flex items-center justify-center font-medium rounded-md transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-1';

    // Variant styles with improved contrast
    const variantStyles = {
      primary:
        'bg-primary-600 text-white hover:bg-primary-700 focus:ring-primary-400 active:bg-primary-800 shadow-sm hover:shadow',
      secondary:
        'bg-gray-200 text-gray-900 hover:bg-gray-300 focus:ring-gray-400 active:bg-gray-400',
      danger:
        'bg-error text-white hover:bg-error-600 focus:ring-error-400 active:bg-error-800',
      outline:
        'bg-white text-primary-700 border border-primary-500 hover:bg-primary-50 focus:ring-primary-400 active:bg-primary-100',
      ghost:
        'bg-transparent text-gray-700 hover:bg-gray-100 focus:ring-gray-400 active:bg-gray-200',
    };

    // Size styles
    const sizeStyles = {
      sm: 'text-xs px-2.5 py-1.5',
      md: 'text-sm px-4 py-2',
      lg: 'text-base px-6 py-3',
    };

    // Icon size based on button size
    const iconSize = {
      sm: 'h-4 w-4',
      md: 'h-5 w-5',
      lg: 'h-6 w-6',
    };

    // Loading spinner - simple implementation
    const LoadingSpinner = () => (
      <svg
        className={clsx('mr-2 -ml-1 animate-spin', iconSize[size])}
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        ></circle>
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        ></path>
      </svg>
    );

    // Construct the combined styles
    const combinedStyles = [
      baseStyles,
      variantStyles[variant],
      sizeStyles[size],
      fullWidth && 'w-full',
      (disabled || loading) &&
        'pointer-events-none cursor-not-allowed opacity-50',
      className,
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <HeadlessButton
        ref={ref}
        type={type}
        disabled={disabled || loading}
        onClick={onClick}
        className={combinedStyles}
        {...props}
      >
        {loading && <LoadingSpinner />}
        {!loading && leftIcon && (
          <Icon src={leftIcon} className={clsx('mr-2', iconSize[size])} />
        )}
        {!loading && leftIconSvg && (
          <Icon svg={leftIconSvg} className={clsx('mr-2', iconSize[size])} />
        )}
        {children}
        {!loading && rightIcon && (
          <Icon src={rightIcon} className={clsx('ml-2', iconSize[size])} />
        )}
        {!loading && rightIconSvg && (
          <Icon svg={rightIconSvg} className={clsx('ml-2', iconSize[size])} />
        )}
      </HeadlessButton>
    );
  }
);

Button.displayName = 'Button';
