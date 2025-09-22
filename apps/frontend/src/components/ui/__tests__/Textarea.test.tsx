import '@testing-library/jest-dom';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Textarea } from '../Textarea';

describe('Textarea', () => {
  it('renders with provided props and forwards native attributes', () => {
    render(<Textarea value="initial" rows={4} placeholder="Enter text" />);

    const el = screen.getByPlaceholderText('Enter text') as HTMLTextAreaElement;
    expect(el).toBeInTheDocument();
    expect(el.value).toBe('initial');
    expect(el.getAttribute('rows')).toBe('4');
  });

  it('applies focus styles by default', () => {
    render(<Textarea value="" placeholder="focus-test" />);
    const el = screen.getByPlaceholderText('focus-test');

    // Default Textarea applies the focus class
    expect(el).toHaveClass('focus:border-blue-500');
  });

  it('does not include focus styles when focus={false}', () => {
    render(<Textarea value="" placeholder="no-focus" focus={false} />);
    const el = screen.getByPlaceholderText('no-focus');

    expect(el).not.toHaveClass('focus:border-blue-500');
    expect(el).not.toHaveClass('focus:ring-2');
  });

  it('forwards onChange and onPaste events', () => {
    const onChange = vi.fn();
    const onPaste = vi.fn();

    render(
      <Textarea
        value=""
        placeholder="events"
        onChange={onChange}
        onPaste={onPaste}
      />
    );

    const el = screen.getByPlaceholderText('events');

    fireEvent.change(el, { target: { value: 'hello' } });
    expect(onChange).toHaveBeenCalled();

    fireEvent.paste(el, {
      clipboardData: { getData: () => 'pasted' },
    } as unknown as Event);
    expect(onPaste).toHaveBeenCalled();
  });
});
