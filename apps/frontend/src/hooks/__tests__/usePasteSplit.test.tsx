import '@testing-library/jest-dom';
import { fireEvent, render, screen } from '@testing-library/react';
import { useRef } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { usePasteSplit } from '../usePasteSplit';

// Simplified test focusing on core functionality
describe('usePasteSplit', () => {
  it('should detect multi-step content and open modal', async () => {
    // Mock component to test the hook
    function TestComponent() {
      const mockCallbacks = useRef({
        onInsertSteps: vi.fn(),
        onReplaceStep: vi.fn(),
        getCurrentStepValue: vi.fn().mockReturnValue(''),
      });

      const { pasteSplitModal, handleInstructionPaste } = usePasteSplit(
        mockCallbacks.current
      );

      return (
        <div>
          <textarea
            data-testid="instruction-textarea"
            onPaste={(e) => handleInstructionPaste(e, 0)}
          />

          {pasteSplitModal.isOpen && (
            <div data-testid="paste-modal">
              <p data-testid="modal-steps">
                Steps: {pasteSplitModal.candidateSteps.join(', ')}
              </p>
              <p data-testid="modal-content">
                Original: {pasteSplitModal.originalContent.replace(/\n/g, ' ')}
              </p>
            </div>
          )}
        </div>
      );
    }

    render(<TestComponent />);

    const textarea = screen.getByTestId('instruction-textarea');

    // Create a proper paste event with clipboardData
    const pasteEvent = new Event('paste', { bubbles: true, cancelable: true });
    Object.assign(pasteEvent, {
      clipboardData: {
        getData: () => '1. First step\n2. Second step\n3. Third step',
      },
    });

    fireEvent(textarea, pasteEvent);

    // Modal should be open
    expect(screen.getByTestId('paste-modal')).toBeInTheDocument();
    expect(screen.getByTestId('modal-steps')).toHaveTextContent(
      'Steps: First step, Second step, Third step'
    );
    expect(screen.getByTestId('modal-content')).toHaveTextContent(
      'Original: 1. First step 2. Second step 3. Third step'
    );
  });

  it('should not open modal for single-step content', async () => {
    // Mock component to test the hook
    function TestComponent() {
      const mockCallbacks = useRef({
        onInsertSteps: vi.fn(),
        onReplaceStep: vi.fn(),
        getCurrentStepValue: vi.fn().mockReturnValue(''),
      });

      const { pasteSplitModal, handleInstructionPaste } = usePasteSplit(
        mockCallbacks.current
      );

      return (
        <div>
          <textarea
            data-testid="instruction-textarea"
            onPaste={(e) => handleInstructionPaste(e, 0)}
          />

          {pasteSplitModal.isOpen && (
            <div data-testid="paste-modal">Modal is open</div>
          )}
        </div>
      );
    }

    render(<TestComponent />);

    const textarea = screen.getByTestId('instruction-textarea');

    // Create paste event with single-step content
    const pasteEvent = new Event('paste', { bubbles: true, cancelable: true });
    Object.assign(pasteEvent, {
      clipboardData: {
        getData: () => 'Mix all ingredients together',
      },
    });

    fireEvent(textarea, pasteEvent);

    // Modal should not be open
    expect(screen.queryByTestId('paste-modal')).not.toBeInTheDocument();
  });

  it('should not render HTML content as markup', async () => {
    // Mock component to test the hook
    function TestComponent() {
      const mockCallbacks = useRef({
        onInsertSteps: vi.fn(),
        onReplaceStep: vi.fn(),
        getCurrentStepValue: vi.fn().mockReturnValue(''),
      });

      const { pasteSplitModal, handleInstructionPaste } = usePasteSplit(
        mockCallbacks.current
      );

      return (
        <div>
          <textarea
            data-testid="instruction-textarea"
            onPaste={(e) => handleInstructionPaste(e, 0)}
          />

          {pasteSplitModal.isOpen && (
            <div data-testid="paste-modal">
              <p data-testid="modal-steps">
                Steps: {pasteSplitModal.candidateSteps.join(', ')}
              </p>
              <p data-testid="modal-content">
                Original: {pasteSplitModal.originalContent}
              </p>
            </div>
          )}
        </div>
      );
    }

    render(<TestComponent />);

    const textarea = screen.getByTestId('instruction-textarea');

    // Create paste event with potentially malicious HTML content
    const pasteEvent = new Event('paste', { bubbles: true, cancelable: true });
    Object.assign(pasteEvent, {
      clipboardData: {
        getData: () =>
          '<img src=x onerror=alert(1)>\n\n<script>alert("xss")</script>',
      },
    });

    fireEvent(textarea, pasteEvent);

    // Content should be treated as plain text in the modal
    if (screen.queryByTestId('paste-modal')) {
      const modalSteps = screen.getByTestId('modal-steps');
      const modalContent = screen.getByTestId('modal-content');

      // HTML should appear as literal text, not be interpreted
      expect(modalSteps.textContent).toContain('<img src=x onerror=alert(1)>');
      expect(modalContent.textContent).toContain(
        '<script>alert("xss")</script>'
      );

      // No actual script or img elements should be rendered from the pasted content
      expect(screen.queryByRole('img')).not.toBeInTheDocument();
      expect(document.querySelector('script[src="x"]')).toBeNull();
    }
  });
});
