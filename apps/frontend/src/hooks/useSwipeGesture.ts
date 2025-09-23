import { useCallback, useRef, useEffect, type RefObject } from 'react';

interface SwipeGestureOptions {
  onSwipeDown?: () => void;
  onSwipeUp?: () => void;
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  threshold?: number; // Minimum distance for a swipe
  velocity?: number; // Minimum velocity for a swipe
}

interface TouchState {
  startX: number;
  startY: number;
  startTime: number;
  isSwiping: boolean;
}

/**
 * Targeted hook for swipe gesture detection on mobile devices
 * Replaces generic useEffect patterns for touch handling
 *
 * @param options - Swipe gesture configuration
 * @returns ref to attach to the swipeable element
 *
 * @example
 * ```tsx
 * const swipeRef = useSwipeGesture({
 *   onSwipeDown: () => setIsOpen(false),
 *   threshold: 50,
 *   velocity: 0.3
 * });
 * return <div ref={swipeRef}>Swipeable content</div>
 * ```
 */
export function useSwipeGesture<T extends HTMLElement>(
  options: SwipeGestureOptions
): RefObject<T> {
  const ref = useRef<T>(null);
  const touchState = useRef<TouchState>({
    startX: 0,
    startY: 0,
    startTime: 0,
    isSwiping: false,
  });

  const {
    onSwipeDown,
    onSwipeUp,
    onSwipeLeft,
    onSwipeRight,
    threshold = 50,
    velocity = 0.3,
  } = options;

  const handleTouchStart = useCallback((event: TouchEvent) => {
    const touch = event.touches[0];
    if (!touch) return;

    touchState.current = {
      startX: touch.clientX,
      startY: touch.clientY,
      startTime: Date.now(),
      isSwiping: true,
    };
  }, []);

  const handleTouchMove = useCallback((event: TouchEvent) => {
    if (!touchState.current.isSwiping) return;

    // Prevent scrolling during swipe detection
    const touch = event.touches[0];
    if (!touch) return;

    const deltaX = Math.abs(touch.clientX - touchState.current.startX);
    const deltaY = Math.abs(touch.clientY - touchState.current.startY);

    // If horizontal movement is greater than vertical, prevent default to stop scrolling
    if (deltaX > deltaY && deltaX > 10) {
      event.preventDefault();
    }
  }, []);

  const handleTouchEnd = useCallback(
    (event: TouchEvent) => {
      if (!touchState.current.isSwiping) return;

      const touch = event.changedTouches[0];
      if (!touch) return;

      const deltaX = touch.clientX - touchState.current.startX;
      const deltaY = touch.clientY - touchState.current.startY;
      const deltaTime = Date.now() - touchState.current.startTime;

      const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
      const calculatedVelocity = distance / deltaTime;

      touchState.current.isSwiping = false;

      // Check if the swipe meets threshold and velocity requirements
      if (distance < threshold || calculatedVelocity < velocity) return;

      // Determine swipe direction
      const absX = Math.abs(deltaX);
      const absY = Math.abs(deltaY);

      if (absX > absY) {
        // Horizontal swipe
        if (deltaX > 0 && onSwipeRight) {
          onSwipeRight();
        } else if (deltaX < 0 && onSwipeLeft) {
          onSwipeLeft();
        }
      } else {
        // Vertical swipe
        if (deltaY > 0 && onSwipeDown) {
          onSwipeDown();
        } else if (deltaY < 0 && onSwipeUp) {
          onSwipeUp();
        }
      }
    },
    [onSwipeDown, onSwipeUp, onSwipeLeft, onSwipeRight, threshold, velocity]
  );

  // Use useEffect for event handling since we need access to the DOM element
  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    element.addEventListener('touchstart', handleTouchStart, {
      passive: false,
    });
    element.addEventListener('touchmove', handleTouchMove, { passive: false });
    element.addEventListener('touchend', handleTouchEnd, { passive: true });

    return () => {
      element.removeEventListener('touchstart', handleTouchStart);
      element.removeEventListener('touchmove', handleTouchMove);
      element.removeEventListener('touchend', handleTouchEnd);
    };
  }, [handleTouchStart, handleTouchMove, handleTouchEnd]);

  return ref;
}
