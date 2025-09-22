import type { DayOption } from '../../types/DayOption';
import { dayButtonAriaLabel } from '../../utils/labelHelpers';
import { Button } from '../ui/Button';
import { Dialog } from '../ui/Dialog';

export interface DaySelectionDialogProps {
  /**
   * Whether the dialog is open
   */
  isOpen: boolean;

  /**
   * Function called when the dialog should be closed
   */
  onClose: () => void;

  /**
   * Function called when a day is selected
   */
  onDaySelect: (dayOfWeek: string, date: string) => void;

  /**
   * The recipe title being added
   */
  recipeTitle: string;

  /**
   * Array of available days to choose from
   */
  availableDays: DayOption[];
}

/**
 * Dialog for selecting which day to add a recipe to on mobile devices
 */
export function DaySelectionDialog({
  isOpen,
  onClose,
  onDaySelect,
  recipeTitle,
  availableDays,
}: DaySelectionDialogProps) {
  const handleDayClick = (dayOfWeek: string, date: string) => {
    onDaySelect(dayOfWeek, date);
    onClose();
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title="Add Recipe to Day"
      size="sm"
    >
      <div className="space-y-4">
        <p className="text-sm text-gray-600">
          Select which day to add{' '}
          <span className="font-medium">{recipeTitle}</span> to:
        </p>

        <div
          className="grid grid-cols-1 gap-2"
          role="group"
          aria-label="Days of the week"
        >
          {availableDays.map(({ dayOfWeek, date, isToday }) => (
            <Button
              key={date}
              variant={isToday ? 'primary' : 'outline'}
              onClick={() => handleDayClick(dayOfWeek, date)}
              className="justify-start text-left"
              fullWidth
              aria-label={dayButtonAriaLabel(dayOfWeek, date, !!isToday)}
              data-variant={isToday ? 'primary' : 'outline'}
              data-testid={`day-button-${dayOfWeek.toLowerCase()}`}
            >
              <span className="flex w-full items-center justify-between">
                <span>{dayOfWeek}</span>
                <span className="ml-2 text-xs text-gray-500">
                  {date}
                  {isToday && ' (Today)'}
                </span>
              </span>
            </Button>
          ))}
        </div>
      </div>
    </Dialog>
  );
}
