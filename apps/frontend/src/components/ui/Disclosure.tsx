import {
  DisclosurePanel,
  Disclosure as HeadlessDisclosure,
} from '@headlessui/react';
import clsx from 'clsx';
import type { ComponentType, ReactNode, SVGProps } from 'react';
import { Icon } from './Icon';
import ChevronUpDown from './icons/chevron-up-down.svg?react';

export interface DisclosureProps {
  /**
   * The title or header of the disclosure
   */
  title: ReactNode;

  /**
   * The content to be shown/hidden
   */
  children: ReactNode;

  /**
   * Whether the disclosure is open by default
   * @default false
   */
  defaultOpen?: boolean;

  /**
   * Callback fired when the disclosure state changes
   */
  onChange?: (open: boolean) => void;

  /**
   * Additional classes for the main disclosure container
   */
  className?: string;

  /**
   * Additional classes for the disclosure button
   */
  buttonClassName?: string;

  /**
   * Additional classes for the disclosure panel
   */
  panelClassName?: string;

  /**
   * Inline SVG component to use instead of the default chevron
   */
  iconSvg?: ComponentType<SVGProps<SVGSVGElement>>;
}

/**
 * Disclosure component based on Headless UI's Disclosure
 *
 * This provides an expandable/collapsible section with proper accessibility
 *
 * @example
 * ```tsx
 * <Disclosure title="Frequently Asked Questions">
 *   <p>This is the content that will be shown or hidden.</p>
 * </Disclosure>
 * ```
 */
export function Disclosure({
  title,
  children,
  defaultOpen = false,
  onChange,
  className = '',
  buttonClassName = '',
  panelClassName = '',
  iconSvg = ChevronUpDown,
}: DisclosureProps) {
  return (
    <HeadlessDisclosure
      as="div"
      className={clsx('rounded-md', className)}
      defaultOpen={defaultOpen}
    >
      {({ open: isOpen }) => (
        <>
          <HeadlessDisclosure.Button
            className={clsx(
              'focus-visible:ring-opacity-75 flex w-full justify-between rounded-lg bg-blue-50 px-4 py-3 text-left text-sm font-medium text-blue-900 hover:bg-blue-100 focus:outline-none focus-visible:ring focus-visible:ring-blue-500',
              buttonClassName
            )}
            onClick={() => {
              onChange?.(!isOpen);
            }}
          >
            <span>{title}</span>
            <Icon
              svg={iconSvg}
              className={clsx(
                'h-5 w-5 text-blue-500 transition-transform',
                isOpen && 'rotate-180 transform'
              )}
              aria-hidden="true"
            />
          </HeadlessDisclosure.Button>

          <DisclosurePanel
            className={clsx(
              'px-4 pt-4 pb-2 text-sm text-gray-700',
              panelClassName
            )}
          >
            {children}
          </DisclosurePanel>
        </>
      )}
    </HeadlessDisclosure>
  );
}
