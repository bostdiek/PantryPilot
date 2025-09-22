import { useState } from 'react';
import { Button } from '../ui/Button';
import { Dialog } from '../ui/Dialog';

interface PasteSplitModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (steps: string[]) => void;
  onCancel: () => void;
  candidateSteps: string[];
}

export function PasteSplitModal({
  isOpen,
  onClose,
  onConfirm,
  onCancel,
  candidateSteps,
}: PasteSplitModalProps) {
  const [editableSteps, setEditableSteps] = useState<string[]>(candidateSteps);

  const handleStepChange = (index: number, value: string) => {
    const newSteps = [...editableSteps];
    newSteps[index] = value;
    setEditableSteps(newSteps);
  };

  const handleRemoveStep = (index: number) => {
    const newSteps = editableSteps.filter((_, i) => i !== index);
    setEditableSteps(newSteps);
  };

  const handleConfirm = () => {
    // Filter out empty steps before confirming
    const filteredSteps = editableSteps.filter((step) => step.trim() !== '');
    onConfirm(filteredSteps);
    onClose();
  };

  const handleCancel = () => {
    onCancel();
    onClose();
  };

  // Reset editable steps when modal opens with new data
  if (isOpen && editableSteps !== candidateSteps) {
    setEditableSteps(candidateSteps);
  }

  return (
    <Dialog
      isOpen={isOpen}
      onClose={handleCancel}
      title="Import Multiple Steps"
      size="lg"
    >
      <div className="space-y-4">
        <div aria-live="polite" className="text-sm text-gray-600">
          Detected {editableSteps.length} step{editableSteps.length !== 1 ? 's' : ''}. 
          You can edit or remove steps before importing.
        </div>

        <div className="space-y-3 max-h-80 overflow-y-auto">
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
                  className="w-full rounded-md border-gray-300 px-3 py-2 resize-vertical whitespace-normal leading-relaxed text-base"
                  value={step}
                  onChange={(e) => handleStepChange(index, e.target.value)}
                  rows={3}
                  placeholder={`Step ${index + 1} content...`}
                />
              </div>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-end space-x-2 pt-4 border-t">
          <Button
            type="button"
            variant="ghost"
            onClick={handleCancel}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="primary"
            onClick={handleConfirm}
            disabled={editableSteps.filter(step => step.trim() !== '').length === 0}
          >
            Import {editableSteps.filter(step => step.trim() !== '').length} Step{editableSteps.filter(step => step.trim() !== '').length !== 1 ? 's' : ''}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}