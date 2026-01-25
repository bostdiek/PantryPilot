import { useNavigate } from 'react-router-dom';
import { Button } from './ui/Button';
import { Dialog } from './ui/Dialog';

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
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title={`Add to ${dayOfWeek}`}
      size="sm"
    >
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

        <button
          onClick={onClose}
          className="mt-4 w-full text-center text-sm text-gray-500 hover:text-gray-700"
        >
          Cancel
        </button>
      </div>
    </Dialog>
  );
}
