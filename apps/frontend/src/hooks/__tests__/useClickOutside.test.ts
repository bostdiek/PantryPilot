import { renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useClickOutside } from '../useClickOutside';

describe('useClickOutside', () => {
  let callback: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    callback = vi.fn();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should call callback when clicking outside the element', () => {
    const { result } = renderHook(() => useClickOutside(callback));

    // Create a mock element
    const element = document.createElement('div');
    result.current.current = element;

    // Simulate a click outside (on document body)
    const outsideElement = document.createElement('div');
    document.body.appendChild(outsideElement);

    const createClickEvent = () => {
      const event = new MouseEvent('click', {
        bubbles: true,
        cancelable: true,
      });
      Object.defineProperty(event, 'target', {
        value: outsideElement,
        enumerable: true,
      });
      return event;
    };

    // First click is skipped (to avoid closing modal on the opening click)
    document.dispatchEvent(createClickEvent());
    expect(callback).not.toHaveBeenCalled();

    // Second click should trigger callback
    document.dispatchEvent(createClickEvent());
    expect(callback).toHaveBeenCalledTimes(1);
  });

  it('should not call callback when clicking inside the element', () => {
    const { result } = renderHook(() => useClickOutside(callback));

    // Create a mock element
    const element = document.createElement('div');
    const childElement = document.createElement('span');
    element.appendChild(childElement);
    result.current.current = element;

    // Simulate a click inside (on child element)
    const event = new MouseEvent('click', {
      bubbles: true,
      cancelable: true,
    });
    Object.defineProperty(event, 'target', {
      value: childElement,
      enumerable: true,
    });

    document.dispatchEvent(event);

    expect(callback).not.toHaveBeenCalled();
  });

  it('should handle touch events', () => {
    const { result } = renderHook(() => useClickOutside(callback));

    // Create a mock element
    const element = document.createElement('div');
    result.current.current = element;

    // Simulate a touch outside
    const outsideElement = document.createElement('div');
    document.body.appendChild(outsideElement);

    const createTouchEvent = () => {
      const event = new TouchEvent('touchend', {
        bubbles: true,
        cancelable: true,
      });
      Object.defineProperty(event, 'target', {
        value: outsideElement,
        enumerable: true,
      });
      return event;
    };

    // First touch is skipped (to avoid closing modal on the opening touch)
    document.dispatchEvent(createTouchEvent());
    expect(callback).not.toHaveBeenCalled();

    // Second touch should trigger callback
    document.dispatchEvent(createTouchEvent());
    expect(callback).toHaveBeenCalledTimes(1);
  });

  it('should not call callback when ref is not set', () => {
    renderHook(() => useClickOutside(callback));

    // Simulate a click without setting ref
    const event = new MouseEvent('click', {
      bubbles: true,
      cancelable: true,
    });
    Object.defineProperty(event, 'target', {
      value: document.body,
      enumerable: true,
    });

    document.dispatchEvent(event);

    expect(callback).not.toHaveBeenCalled();
  });

  it('should not call callback when active is false', () => {
    const { result } = renderHook(() => useClickOutside(callback, false));

    // Create a mock element
    const element = document.createElement('div');
    result.current.current = element;

    // Simulate a click outside
    const outsideElement = document.createElement('div');
    document.body.appendChild(outsideElement);

    const event = new MouseEvent('click', {
      bubbles: true,
      cancelable: true,
    });
    Object.defineProperty(event, 'target', {
      value: outsideElement,
      enumerable: true,
    });

    document.dispatchEvent(event);

    expect(callback).not.toHaveBeenCalled();
  });

  it('should call callback when active is true', () => {
    const { result } = renderHook(() => useClickOutside(callback, true));

    // Create a mock element
    const element = document.createElement('div');
    result.current.current = element;

    // Simulate a click outside
    const outsideElement = document.createElement('div');
    document.body.appendChild(outsideElement);

    const createClickEvent = () => {
      const event = new MouseEvent('click', {
        bubbles: true,
        cancelable: true,
      });
      Object.defineProperty(event, 'target', {
        value: outsideElement,
        enumerable: true,
      });
      return event;
    };

    // First click is skipped
    document.dispatchEvent(createClickEvent());
    expect(callback).not.toHaveBeenCalled();

    // Second click should trigger callback
    document.dispatchEvent(createClickEvent());
    expect(callback).toHaveBeenCalledTimes(1);
  });
});
