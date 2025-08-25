export type InputType =
  | 'text'
  | 'email'
  | 'password'
  | 'number'
  | 'search'
  | 'tel'
  | 'url';
export type InputSize = 'sm' | 'md' | 'lg';
export type InputVariant = 'outline' | 'filled' | 'unstyled';

export interface InputProps {
  /** Input value */
  value: string;
  /** Change handler */
  onChange: (value: string) => void;
  /** Input type */
  type?: InputType;
  /** Placeholder text */
  placeholder?: string;
  /** Input label */
  label?: string;
  /** Helper text displayed below the input */
  helperText?: string;
  /** Error message to display */
  error?: string;
  /** Input size */
  size?: InputSize;
  /** Visual style variant */
  variant?: InputVariant;
  /** Whether the input is required */
  required?: boolean;
  /** ID for the input element (for accessibility and form association) */
  id?: string;
  /** Name attribute for the input (important for form submission) */
  name?: string;
  /** Icon to display at the start of the input */
  leftIcon?: string;
  /** Icon to display at the end of the input */
  rightIcon?: string;
  /** HTML autocomplete attribute */
  autoComplete?: string;
  /** Blur event handler */
  onBlur?: () => void;
  /** Disables the input */
  disabled?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Input component for text input fields
 *
 * This provides a custom styled input with proper accessibility
 *
 * @example
 * ```tsx
 * <Input
 *   value={value}
 *   onChange={setValue}
 *   type="text"
 *   placeholder="Enter text"
 *   label="Text Input"
 *   helperText="This is a helper text"
 * />
 * ```
 */
import clsx from 'clsx';
import { useId } from 'react';
import { inputSizes } from './tokens';

export function Input({
  value,
  onChange,
  type = 'text',
  placeholder = '',
  label,
  helperText,
  error,
  size = 'md',
  variant = 'outline',
  required = false,
  id,
  name,
  leftIcon,
  rightIcon,
  autoComplete,
  onBlur,
  disabled = false,
  className = '',
}: InputProps) {
  // Generate an ID if not provided (for associating label and help/error text)
  const autoId = useId();
  const inputId = id || `input-${autoId}`;
  const helperId = `helper-${inputId}`;

  // Determine sizing classes
  const sizeClasses = inputSizes;

  // Determine variant classes
  const variantClasses = {
    outline:
      'bg-white border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
    filled:
      'bg-gray-100 border border-transparent focus:ring-2 focus:ring-blue-500',
    unstyled: 'border-none shadow-none bg-transparent p-0 focus:ring-0',
  };

  return (
    <div className={clsx('flex flex-col', className)}>
      {label && (
        <label
          htmlFor={inputId}
          className="mb-1 text-sm font-medium text-gray-700"
        >
          {label}
          {required && <span className="ml-1 text-red-500">*</span>}
        </label>
      )}

      <div className="relative">
        {leftIcon && (
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
            <img
              src={leftIcon}
              className="h-5 w-5 text-gray-500"
              aria-hidden="true"
            />
          </div>
        )}

        <input
          id={inputId}
          name={name}
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          placeholder={placeholder}
          disabled={disabled}
          required={required}
          autoComplete={autoComplete}
          aria-describedby={helperText || error ? helperId : undefined}
          aria-invalid={!!error}
          aria-required={required}
          className={clsx(
            'w-full rounded-md transition-colors outline-none',
            sizeClasses[size],
            variantClasses[variant],
            error &&
              'border-red-500 text-red-900 focus:border-red-500 focus:ring-red-500',
            disabled && 'cursor-not-allowed opacity-60',
            leftIcon && 'pl-10',
            rightIcon && 'pr-10'
          )}
        />

        {rightIcon && (
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
            <img
              src={rightIcon}
              className="h-5 w-5 text-gray-500"
              aria-hidden="true"
            />
          </div>
        )}
      </div>

      {(helperText || error) && (
        <p
          id={helperId}
          className={clsx(
            'mt-1 text-xs',
            error ? 'text-red-600' : 'text-gray-500'
          )}
        >
          {error || helperText}
        </p>
      )}
    </div>
  );
}
