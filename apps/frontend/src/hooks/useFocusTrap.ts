import { useCallback, useRef, useEffect, useLayoutEffect, type RefObject } from 'react';

interface FocusTrapOptions {
  active?: boolean;
  initialFocus?: string; // CSS selector for element to focus on mount
  restoreFocus?: boolean; // Whether to restore focus when trap is deactivated
}

/**
 * Targeted hook for focus management in modals and overlays
 * Ensures keyboard accessibility by trapping focus within a container
 * 
 * @param options - Focus trap configuration
 * @returns ref to attach to the container that should trap focus
 * 
 * @example
 * ```tsx
 * const trapRef = useFocusTrap({
 *   active: isOpen,
 *   initialFocus: 'button',
 *   restoreFocus: true
 * });
 * return <div ref={trapRef}>Modal content with trapped focus</div>
 * ```
 */
export function useFocusTrap<T extends HTMLElement>(
  options: FocusTrapOptions = {}
): RefObject<T> {
  const ref = useRef<T>(null);
  const previousActiveElement = useRef<Element | null>(null);
  const { active = true, initialFocus, restoreFocus = true } = options;

  // Get all focusable elements within the container
  const getFocusableElements = useCallback(() => {
    const element = ref.current;
    if (!element) return [];

    const focusableSelectors = [
      'button:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      'textarea:not([disabled])',
      'a[href]',
      '[tabindex]:not([tabindex="-1"])',
      '[contenteditable="true"]',
    ].join(', ');

    return Array.from(element.querySelectorAll(focusableSelectors)) as HTMLElement[];
  }, []);

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (event.key !== 'Tab') return;

    const focusableElements = getFocusableElements();
    if (focusableElements.length === 0) return;

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    if (event.shiftKey) {
      // Shift + Tab (backwards)
      if (document.activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
      }
    } else {
      // Tab (forwards)
      if (document.activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    }
  }, [getFocusableElements]);

  // Set initial focus using useLayoutEffect to avoid flicker
  const setInitialFocus = useCallback(() => {
    const element = ref.current;
    if (!element) return;

    let targetElement: HTMLElement | null = null;

    if (initialFocus) {
      targetElement = element.querySelector(initialFocus) as HTMLElement;
    }

    if (!targetElement) {
      const focusableElements = getFocusableElements();
      targetElement = focusableElements[0] || null;
    }

    if (targetElement) {
      targetElement.focus();
    }
  }, [initialFocus, getFocusableElements]);

  // Use useLayoutEffect for initial focus to prevent flicker
  useLayoutEffect(() => {
    if (active) {
      setInitialFocus();
    }
  }, [active, setInitialFocus]);

  useEffect(() => {
    if (!active) return;

    // Store the previously focused element
    previousActiveElement.current = document.activeElement;

    // Add event listener
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      
      // Restore focus to the previously active element
      if (restoreFocus && previousActiveElement.current instanceof HTMLElement) {
        setTimeout(() => {
          if (previousActiveElement.current instanceof HTMLElement) {
            previousActiveElement.current.focus();
          }
        }, 0);
      }
    };
  }, [active, handleKeyDown, restoreFocus]);

  return ref;
}