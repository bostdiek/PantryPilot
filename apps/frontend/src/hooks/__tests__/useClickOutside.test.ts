import { renderHook } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
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

    const event = new MouseEvent('mousedown', {
      bubbles: true,
      cancelable: true,
    });
    Object.defineProperty(event, 'target', {
      value: outsideElement,
      enumerable: true,
    });

    document.dispatchEvent(event);

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
    const event = new MouseEvent('mousedown', {
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

    const event = new TouchEvent('touchstart', {
      bubbles: true,
      cancelable: true,
    });
    Object.defineProperty(event, 'target', {
      value: outsideElement,
      enumerable: true,
    });

    document.dispatchEvent(event);

    expect(callback).toHaveBeenCalledTimes(1);
  });

  it('should not call callback when ref is not set', () => {
    renderHook(() => useClickOutside(callback));

    // Simulate a click without setting ref
    const event = new MouseEvent('mousedown', {
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
});