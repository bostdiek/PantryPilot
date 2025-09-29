import '@testing-library/jest-dom';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { PasteSplitModal } from '../PasteSplitModal';

// Mock the trash icon
vi.mock('../../ui/icons/trash.svg?react', () => ({
  default: () => <div data-testid="mock-trash-icon" />,
}));

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

    // Test that we can remove a step using the trash icon
    const removeButtons = screen.getAllByLabelText(/remove step/i);
    expect(removeButtons).toHaveLength(2); // Should have remove buttons for both steps
    
    // Remove the first step
    fireEvent.click(removeButtons[0]);
    
    // Should now only have one step (what was Step 2 becomes Step 1)
    expect(screen.getAllByLabelText(/^Step \d+$/)).toHaveLength(1);
    expect(screen.getByLabelText('Step 1')).toHaveValue('Step B'); // Step B becomes the new Step 1
  });
});
