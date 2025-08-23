import { Dialog as HeadlessDialog, Transition } from '@headlessui/react';
import type { ReactNode } from 'react';
import { Fragment } from 'react';
import type { ButtonProps } from './Button';
import { Button } from './Button';
import { dialogSizes } from './tokens';

export type DialogSize = 'sm' | 'md' | 'lg' | 'xl' | 'full';

export interface DialogProps {
  /**
   * Whether the dialog is open or not
   */
  isOpen: boolean;

  /**
   * Function to call when the dialog should be closed
   */
  onClose: () => void;

  /**
   * The title of the dialog
   */
  title?: ReactNode;

  /**
   * The description of the dialog
   */
  description?: ReactNode;

  /**
   * The content of the dialog
   */
  children: ReactNode;

  /**
   * The size of the dialog
   * @default 'md'
   */
  size?: DialogSize;

  /**
   * The footer of the dialog, typically containing action buttons
   */
  footer?: ReactNode;

  /**
   * If true, clicking outside the dialog will not close it
   * @default false
   */
  static?: boolean;

  /**
   * Additional classes for the dialog panel
   */
  className?: string;
}

/**
 * Dialog component based on Headless UI's Dialog
 *
 * This provides an accessible modal dialog with background overlay
 *
 * @example
 * ```tsx
 * const [isOpen, setIsOpen] = useState(false);
 *
 * <Button onClick={() => setIsOpen(true)}>Open Dialog</Button>
 *
 * <Dialog isOpen={isOpen} onClose={() => setIsOpen(false)} title="Confirm Action">
 *   <p>Are you sure you want to proceed with this action?</p>
 *   <div className="mt-4 flex justify-end space-x-2">
 *     <Button variant="outline" onClick={() => setIsOpen(false)}>Cancel</Button>
 *     <Button onClick={() => { console.log('Confirmed!'); setIsOpen(false); }}>Confirm</Button>
 *   </div>
 * </Dialog>
 * ```
 */
export function Dialog({
  isOpen,
  onClose,
  title,
  description,
  children,
  size = 'md',
  footer,
  static: isStatic = false,
  className = '',
}: DialogProps) {
  // Size classes for the dialog
  const sizeClasses = dialogSizes;

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <HeadlessDialog
        as="div"
        className="relative z-50"
        onClose={isStatic ? () => {} : onClose}
        static={isStatic}
      >
        {/* Background overlay */}
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div
            className="fixed inset-0 bg-black/30 backdrop-blur-sm"
            aria-hidden="true"
          />
        </Transition.Child>

        {/* Dialog panel */}
        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <HeadlessDialog.Panel
                className={`w-full ${sizeClasses[size]} transform overflow-hidden rounded-lg bg-white p-6 text-left align-middle shadow-xl transition-all ${className}`}
              >
                {/* Title */}
                {title && (
                  <HeadlessDialog.Title
                    as="h3"
                    className="text-lg leading-6 font-medium text-gray-900"
                  >
                    {title}
                  </HeadlessDialog.Title>
                )}

                {/* Description */}
                {description && (
                  <HeadlessDialog.Description className="mt-2 text-sm text-gray-500">
                    {description}
                  </HeadlessDialog.Description>
                )}

                {/* Content */}
                <div className={title || description ? 'mt-4' : undefined}>
                  {children}
                </div>

                {/* Footer */}
                {footer && <div className="mt-6">{footer}</div>}
              </HeadlessDialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </HeadlessDialog>
    </Transition>
  );
}

/**
 * DialogFooter component for standardized dialog action buttons
 */
export function DialogFooter({
  cancelText = 'Cancel',
  confirmText = 'Confirm',
  onCancel,
  onConfirm,
  cancelProps,
  confirmProps,
  className = '',
  children,
}: {
  cancelText?: string;
  confirmText?: string;
  onCancel?: () => void;
  onConfirm?: () => void;
  cancelProps?: Partial<ButtonProps>;
  confirmProps?: Partial<ButtonProps>;
  className?: string;
  children?: ReactNode;
}) {
  return (
    <div className={`mt-6 flex justify-end space-x-3 ${className}`}>
      {children ||
        (onCancel || onConfirm ? (
          <>
            {onCancel && (
              <Button variant="outline" onClick={onCancel} {...cancelProps}>
                {cancelText}
              </Button>
            )}
            {onConfirm && (
              <Button variant="primary" onClick={onConfirm} {...confirmProps}>
                {confirmText}
              </Button>
            )}
          </>
        ) : null)}
    </div>
  );
}
