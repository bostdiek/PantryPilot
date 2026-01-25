import {
  Dialog,
  DialogPanel,
  DialogTitle,
  Transition,
  TransitionChild,
} from '@headlessui/react';
import { Fragment } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from './ui/Button';

export interface AddMealDialogProps {
  /**
   * Whether the dialog is open
   */
  isOpen: boolean;

  /**
   * Callback when the dialog should close
   */
  onClose: () => void;

  /**
   * Target date in YYYY-MM-DD format
   */
  targetDate: string;

  /**
   * Day of week label (e.g., "Sunday")
   */
  dayOfWeek: string;

  /**
   * Callback to add a leftover entry
   */
  onAddLeftover: () => void;

  /**
   * Callback to add an eating out entry
   */
  onAddEatingOut: () => void;
}

/**
 * Dialog for adding meals to a day.
 * Provides options for Recipe, Leftover, or Eating Out.
 *
 * - Recipe navigates to /recipes with addToDate query params
 * - Leftover and Eating Out add entries directly via callbacks
 */
export function AddMealDialog({
  isOpen,
  onClose,
  targetDate,
  dayOfWeek,
  onAddLeftover,
  onAddEatingOut,
}: AddMealDialogProps) {
  const navigate = useNavigate();

  const handleRecipe = () => {
    navigate(
      `/recipes?addToDate=${targetDate}&dayLabel=${encodeURIComponent(dayOfWeek)}`
    );
    onClose();
  };

  const handleLeftover = () => {
    onAddLeftover();
    onClose();
  };

  const handleEatingOut = () => {
    onAddEatingOut();
    onClose();
  };

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        {/* Backdrop */}
        <TransitionChild
          as={Fragment}
          enter="ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-150"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/25" aria-hidden="true" />
        </TransitionChild>

        {/* Dialog content */}
        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <TransitionChild
              as={Fragment}
              enter="ease-out duration-200"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-150"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <DialogPanel className="w-full max-w-sm transform rounded-2xl bg-white p-6 shadow-xl transition-all">
                <DialogTitle className="mb-4 text-center text-lg font-semibold">
                  Add to {dayOfWeek}
                </DialogTitle>

                <div className="space-y-3">
                  <Button
                    fullWidth
                    variant="primary"
                    onClick={handleRecipe}
                    className="min-h-[44px]"
                  >
                    🍽️ Add Recipe
                  </Button>
                  <Button
                    fullWidth
                    variant="outline"
                    onClick={handleLeftover}
                    className="min-h-[44px]"
                  >
                    ♻️ Leftovers
                  </Button>
                  <Button
                    fullWidth
                    variant="outline"
                    onClick={handleEatingOut}
                    className="min-h-[44px]"
                  >
                    🍔 Eating Out
                  </Button>
                </div>

                <button
                  onClick={onClose}
                  className="mt-4 w-full text-center text-sm text-gray-500 hover:text-gray-700"
                >
                  Cancel
                </button>
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}
