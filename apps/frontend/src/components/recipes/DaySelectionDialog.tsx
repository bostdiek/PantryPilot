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
  availableDays: Array<{
    dayOfWeek: string;
    date: string;
    isToday?: boolean;
  }>;
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
          Select which day to add <span className="font-medium">{recipeTitle}</span> to:
        </p>
        
        <div className="grid grid-cols-1 gap-2">
          {availableDays.map(({ dayOfWeek, date, isToday }) => (
            <Button
              key={date}
              variant={isToday ? 'primary' : 'outline'}
              onClick={() => handleDayClick(dayOfWeek, date)}
              className="justify-start text-left"
              fullWidth
            >
              <span className="flex items-center justify-between w-full">
                <span>{dayOfWeek}</span>
                <span className="text-xs text-gray-500 ml-2">
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