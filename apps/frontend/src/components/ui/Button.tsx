import { Button as HeadlessButton } from '@headlessui/react';
import type { ReactNode } from 'react';
import { forwardRef } from 'react';
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
   */
  leftIcon?: string;

  /**
   * Right icon path (from our icons directory)
   */
  rightIcon?: string;

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
      className = '',
      onClick,
      type = 'button',
      ...props
    },
    ref
  ) => {
    // Base styles
    const baseStyles =
      'inline-flex items-center justify-center font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2';

    // Variant styles
    const variantStyles = {
      primary:
        'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500 data-active:bg-blue-800',
      secondary:
        'bg-gray-200 text-gray-800 hover:bg-gray-300 focus:ring-gray-500 data-active:bg-gray-400',
      danger:
        'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500 data-active:bg-red-800',
      outline:
        'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50 focus:ring-blue-500 data-active:bg-gray-100',
      ghost:
        'bg-transparent text-gray-700 hover:bg-gray-100 focus:ring-gray-500 data-active:bg-gray-200',
    };

    // Size styles
    const sizeStyles = {
      sm: 'text-xs px-2.5 py-1.5',
      md: 'text-sm px-4 py-2',
      lg: 'text-base px-6 py-3',
    };

    // Full width style
    const widthStyle = fullWidth ? 'w-full' : '';

    // Disabled style
    const disabledStyle =
      disabled || loading
        ? 'opacity-50 cursor-not-allowed pointer-events-none'
        : '';

    // Combined styles
    const combinedStyles = `
      ${baseStyles}
      ${variantStyles[variant]}
      ${sizeStyles[size]}
      ${widthStyle}
      ${disabledStyle}
      ${className}
    `;

    // Icon size based on button size
    const iconSize = {
      sm: 'h-4 w-4',
      md: 'h-5 w-5',
      lg: 'h-6 w-6',
    };

    // Loading spinner - simple implementation
    const LoadingSpinner = () => (
      <svg
        className={`mr-2 -ml-1 animate-spin ${iconSize[size]}`}
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
          <Icon src={leftIcon} className={`mr-2 ${iconSize[size]}`} />
        )}
        {children}
        {!loading && rightIcon && (
          <Icon src={rightIcon} className={`ml-2 ${iconSize[size]}`} />
        )}
      </HeadlessButton>
    );
  }
);

Button.displayName = 'Button';
