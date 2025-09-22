import '@testing-library/jest-dom';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { PasteSplitModal } from '../PasteSplitModal';

describe('PasteSplitModal', () => {
  it('renders candidate steps and disables focus styling on preview textareas', () => {
    const onClose = vi.fn();
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    const onPasteAsSingle = vi.fn();

    render(
      <PasteSplitModal
        isOpen={true}
        onClose={onClose}
        onConfirm={onConfirm}
        onCancel={onCancel}
        onPasteAsSingle={onPasteAsSingle}
        candidateSteps={['Step A', 'Step B']}
        originalContent={'Full pasted content'}
      />
    );

    // Ensure both preview textareas are rendered with correct initial values
    const step1 = screen.getByLabelText('Step 1') as HTMLTextAreaElement;
    const step2 = screen.getByLabelText('Step 2') as HTMLTextAreaElement;

    expect(step1).toBeInTheDocument();
    expect(step2).toBeInTheDocument();
    expect(step1.value).toBe('Step A');
    expect(step2.value).toBe('Step B');

    // The preview textareas use the shared Textarea with focus={false} so they
    // should not include focus-related classes
    expect(step1).not.toHaveClass('focus:border-blue-500');
    expect(step1).not.toHaveClass('focus:ring-2');

    // Clicking "Paste as Single Step" should call the handler with original content
    const pasteSingle = screen.getByText('Paste as Single Step');
    fireEvent.click(pasteSingle);
    expect(onPasteAsSingle).toHaveBeenCalledWith('Full pasted content');
  });
});
