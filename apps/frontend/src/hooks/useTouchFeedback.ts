import { useCallback, useRef, useEffect, type RefObject } from 'react';

interface TouchFeedbackOptions {
  activeClass?: string;
  onTouchStart?: () => void;
  onTouchEnd?: () => void;
  hapticFeedback?: boolean;
}

/**
 * Targeted hook for consistent touch interaction patterns
 * Provides visual and haptic feedback for mobile interactions
 * 
 * @param options - Touch feedback configuration
 * @returns ref to attach to the touchable element
 * 
 * @example
 * ```tsx
 * const touchRef = useTouchFeedback({
 *   activeClass: 'bg-gray-100',
 *   hapticFeedback: true,
 *   onTouchStart: () => console.log('touch started')
 * });
 * return <button ref={touchRef}>Touchable button</button>
 * ```
 */
export function useTouchFeedback<T extends HTMLElement>(
  options: TouchFeedbackOptions = {}
): RefObject<T> {
  const ref = useRef<T>(null);
  const {
    activeClass = 'touch-active',
    onTouchStart,
    onTouchEnd,
    hapticFeedback = false,
  } = options;

  const handleTouchStart = useCallback(() => {
    const element = ref.current;
    if (!element) return;

    // Add active class for visual feedback
    element.classList.add(activeClass);

    // Haptic feedback if supported and enabled
    if (hapticFeedback && typeof navigator.vibrate === 'function') {
      navigator.vibrate(10); // Short vibration
    }

    onTouchStart?.();
  }, [activeClass, onTouchStart, hapticFeedback]);

  const handleTouchEnd = useCallback(() => {
    const element = ref.current;
    if (!element) return;

    // Remove active class
    element.classList.remove(activeClass);

    onTouchEnd?.();
  }, [activeClass, onTouchEnd]);

  const handleTouchCancel = useCallback(() => {
    const element = ref.current;
    if (!element) return;

    // Remove active class on cancel
    element.classList.remove(activeClass);
  }, [activeClass]);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    // Add touch event listeners
    element.addEventListener('touchstart', handleTouchStart, { passive: true });
    element.addEventListener('touchend', handleTouchEnd, { passive: true });
    element.addEventListener('touchcancel', handleTouchCancel, { passive: true });

    return () => {
      element.removeEventListener('touchstart', handleTouchStart);
      element.removeEventListener('touchend', handleTouchEnd);
      element.removeEventListener('touchcancel', handleTouchCancel);
      
      // Clean up any remaining active class
      element.classList.remove(activeClass);
    };
  }, [handleTouchStart, handleTouchEnd, handleTouchCancel, activeClass]);

  return ref;
}