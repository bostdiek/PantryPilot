import { useState, useCallback } from 'react';
import type { ClipboardEvent } from 'react';
import { looksMultiStep, splitSteps } from '../utils/pasteHelpers';

interface UsePasteSplitOptions {
  onInsertSteps: (
    targetIndex: number,
    steps: string[],
    replaceEmpty?: boolean
  ) => void;
  onReplaceStep: (targetIndex: number, content: string) => void;
  getCurrentStepValue: (index: number) => string;
}

interface PasteSplitModalState {
  isOpen: boolean;
  targetIndex: number;
  candidateSteps: string[];
  originalContent: string;
}

export function usePasteSplit({
  onInsertSteps,
  onReplaceStep,
  getCurrentStepValue,
}: UsePasteSplitOptions) {
  const [pasteSplitModal, setPasteSplitModal] = useState<PasteSplitModalState>({
    isOpen: false,
    targetIndex: -1,
    candidateSteps: [],
    originalContent: '',
  });

  const handleInstructionPaste = useCallback(
    (e: ClipboardEvent<HTMLTextAreaElement>, idx: number) => {
      const text = e.clipboardData.getData('text');

      if (!looksMultiStep(text)) {
        // Allow normal paste for single-step content
        return;
      }

      // Prevent default paste behavior
      e.preventDefault();

      const steps = splitSteps(text);
      if (steps.length <= 1) {
        // If splitting didn't result in multiple steps, allow normal paste
        const textarea = e.target as HTMLTextAreaElement;
        const currentValue = textarea.value;
        const selectionStart = textarea.selectionStart;
        const selectionEnd = textarea.selectionEnd;

        const newValue =
          currentValue.substring(0, selectionStart) +
          text +
          currentValue.substring(selectionEnd);
        onReplaceStep(idx, newValue);
        return;
      }

      // Open modal for multi-step confirmation
      setPasteSplitModal({
        isOpen: true,
        targetIndex: idx,
        candidateSteps: steps,
        originalContent: text,
      });
    },
    [onReplaceStep]
  );

  const handlePasteSplitConfirm = useCallback(
    (steps: string[]) => {
      const targetIdx = pasteSplitModal.targetIndex;

      // Guard against invalid targetIndex - delegate to parent for validation
      if (targetIdx < 0) {
        console.warn(
          `Invalid target index ${targetIdx}, cannot confirm paste split`
        );
        return;
      }

      // Check if target step is empty and should be replaced
      const replaceEmpty = getCurrentStepValue(targetIdx).trim() === '';
      onInsertSteps(targetIdx, steps, replaceEmpty);
    },
    [pasteSplitModal.targetIndex, onInsertSteps, getCurrentStepValue]
  );

  const handlePasteAsSingle = useCallback(
    (content: string) => {
      const targetIdx = pasteSplitModal.targetIndex;

      // Guard against invalid targetIndex
      if (targetIdx < 0) {
        console.warn(
          `Invalid target index ${targetIdx}, cannot paste as single step`
        );
        return;
      }

      onReplaceStep(targetIdx, content);
    },
    [pasteSplitModal.targetIndex, onReplaceStep]
  );

  const handlePasteSplitCancel = useCallback(() => {
    // Do nothing - user cancelled the split
  }, []);

  const closePasteSplitModal = useCallback(() => {
    setPasteSplitModal((prev) => ({ ...prev, isOpen: false }));
  }, []);

  return {
    pasteSplitModal,
    handleInstructionPaste,
    handlePasteSplitConfirm,
    handlePasteAsSingle,
    handlePasteSplitCancel,
    closePasteSplitModal,
  };
}
