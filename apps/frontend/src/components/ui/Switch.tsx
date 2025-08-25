import { Switch as HeadlessSwitch } from '@headlessui/react';
import type { ReactNode } from 'react';
import { useId } from 'react';
import clsx from 'clsx';
import { switchKnobSizes, switchTrackSizes } from './tokens';

export interface SwitchProps {
  /**
   * Whether the switch is checked/enabled
   */
  checked: boolean;

  /**
   * Function to call when the switch is toggled
   */
  onChange: (checked: boolean) => void;

  /**
   * The label for the switch (optional)
   */
  label?: ReactNode;

  /**
   * The description for the switch (optional)
   */
  description?: ReactNode;

  /**
   * Whether the switch is disabled
   * @default false
   */
  disabled?: boolean;

  /**
   * The name to use when used inside a form
   */
  name?: string;

  /**
   * The value to use when used inside a form (if checked)
   * @default 'on'
   */
  value?: string;

  /**
   * Additional classes for the switch
   */
  className?: string;

  /**
   * Additional classes for the label
   */
  labelClassName?: string;

  /**
   * Additional classes for the description
   */
  descriptionClassName?: string;

  /**
   * Whether clicking the label should toggle the switch
   * @default true
   */
  labelClickable?: boolean;

  /**
   * Size of the switch
   * @default 'md'
   */
  size?: 'sm' | 'md' | 'lg';
}

/**
 * Switch component based on Headless UI's Switch
 *
 * This provides an accessible toggle switch with proper ARIA attributes
 *
 * @example
 * ```tsx
 * const [enabled, setEnabled] = useState(false);
 *
 * <Switch
 *   checked={enabled}
 *   onChange={setEnabled}
 *   label="Enable notifications"
 * />
 * ```
 */
export function Switch({
  checked,
  onChange,
  label,
  description,
  disabled = false,
  name,
  value,
  className = '',
  labelClassName = '',
  descriptionClassName = '',
  labelClickable = true,
  size = 'md',
}: SwitchProps) {
  const id = useId();

  // Size classes for the switch
  const switchSizeClasses = switchTrackSizes;

  // Size classes for the switch knob/handle
  const knobSizeClasses = switchKnobSizes;

  // If there's a label or description, render with a wrapper for layout
  if (label || description) {
    return (
      <div className={clsx('flex items-start', disabled && 'opacity-50')}>
        <HeadlessSwitch.Group>
          <div className="flex flex-col">
            {label && (
              <HeadlessSwitch.Label
                passive={!labelClickable}
                className={clsx(
                  'mb-1 text-sm font-medium text-gray-700',
                  labelClassName
                )}
              >
                {label}
              </HeadlessSwitch.Label>
            )}
            {description && (
              <div
                className={clsx('text-xs text-gray-500', descriptionClassName)}
              >
                {description}
              </div>
            )}
          </div>

          <div className="ml-auto">
            <HeadlessSwitch
              checked={checked}
              onChange={onChange}
              disabled={disabled}
              name={name}
              value={value}
              className={clsx(
                'group relative inline-flex',
                switchSizeClasses[size],
                'items-center rounded-full bg-gray-200 transition-colors focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:outline-none data-[checked]:bg-blue-600 data-[disabled]:cursor-not-allowed',
                className
              )}
              id={id}
            >
              <span className="sr-only">{label || 'Toggle'}</span>
              <span
                className={clsx(
                  knobSizeClasses[size],
                  'rounded-full bg-white transition-transform'
                )}
                aria-hidden="true"
              />
            </HeadlessSwitch>
          </div>
        </HeadlessSwitch.Group>
      </div>
    );
  }

  // Simple switch without label or description
  return (
    <HeadlessSwitch
      checked={checked}
      onChange={onChange}
      disabled={disabled}
      name={name}
      value={value}
      className={clsx(
        'group relative inline-flex',
        switchSizeClasses[size],
        'items-center rounded-full bg-gray-200 transition-colors focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:outline-none data-[checked]:bg-blue-600 data-[disabled]:cursor-not-allowed',
        disabled && 'opacity-50',
        className
      )}
    >
      <span className="sr-only">{label || 'Toggle'}</span>
      <span
        className={clsx(
          knobSizeClasses[size],
          'rounded-full bg-white transition-transform'
        )}
        aria-hidden="true"
      />
    </HeadlessSwitch>
  );
}
