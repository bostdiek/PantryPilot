import { useState, useEffect } from 'react';
import { Button } from '../ui/Button';
import { Dialog } from '../ui/Dialog';

interface PasteSplitModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (steps: string[]) => void;
  onCancel: () => void;
  onPasteAsSingle: (content: string) => void;
  candidateSteps: string[];
  originalContent: string;
}

export function PasteSplitModal({
  isOpen,
  onClose,
  onConfirm,
  onCancel,
  onPasteAsSingle,
  candidateSteps,
  originalContent,
}: PasteSplitModalProps) {
  const [editableSteps, setEditableSteps] = useState<string[]>(candidateSteps);

  // Properly synchronize state when modal opens with new data
  useEffect(() => {
    if (isOpen) {
      setEditableSteps([...candidateSteps]);
    }
  }, [isOpen, candidateSteps]);

  const handleStepChange = (index: number, value: string) => {
    const newSteps = [...editableSteps];
    newSteps[index] = value;
    setEditableSteps(newSteps);
  };

  const handleRemoveStep = (index: number) => {
    const newSteps = editableSteps.filter((_, i) => i !== index);
    setEditableSteps(newSteps);
  };

  const handleConfirmMultiple = () => {
    // Filter out empty steps before confirming
    const filteredSteps = editableSteps.filter((step) => step.trim() !== '');
    onConfirm(filteredSteps);
    onClose();
  };

  const handlePasteSingle = () => {
    onPasteAsSingle(originalContent);
    onClose();
  };

  const handleCancel = () => {
    onCancel();
    onClose();
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={handleCancel}
      title="Import Multiple Steps"
      size="lg"
    >
      <div className="space-y-4">
        <div aria-live="polite" className="text-sm text-gray-600">
          Detected {editableSteps.length} step
          {editableSteps.length !== 1 ? 's' : ''}. You can edit or remove steps
          before importing.
        </div>

        <div className="max-h-80 space-y-3 overflow-y-auto">
          {editableSteps.map((step, index) => (
            <div key={index} className="space-y-1">
              <div className="flex items-center justify-between">
                <label
                  className="block text-sm font-medium text-gray-700"
                  htmlFor={`step-preview-${index}`}
                >
                  Step {index + 1}
                </label>
                {editableSteps.length > 1 && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRemoveStep(index)}
                    aria-label={`Remove step ${index + 1}`}
                  >
                    Remove
                  </Button>
                )}
              </div>
              {/* Apply reading width constraint to the textarea preview */}
              <div className="mx-auto max-w-prose">
                <textarea
                  id={`step-preview-${index}`}
                  className="resize-vertical w-full rounded-md border-gray-300 px-3 py-2 text-base leading-relaxed whitespace-normal"
                  value={step}
                  onChange={(e) => handleStepChange(index, e.target.value)}
                  rows={3}
                  placeholder={`Step ${index + 1} content...`}
                />
              </div>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between space-x-2 border-t pt-4">
          <Button type="button" variant="ghost" onClick={handleCancel}>
            Cancel
          </Button>

          <div className="flex space-x-2">
            <Button type="button" variant="outline" onClick={handlePasteSingle}>
              Paste as Single Step
            </Button>
            <Button
              type="button"
              variant="primary"
              onClick={handleConfirmMultiple}
              disabled={
                editableSteps.filter((step) => step.trim() !== '').length === 0
              }
            >
              Import {editableSteps.filter((step) => step.trim() !== '').length}{' '}
              Step
              {editableSteps.filter((step) => step.trim() !== '').length !== 1
                ? 's'
                : ''}
            </Button>
          </div>
        </div>
      </div>
    </Dialog>
  );
}
