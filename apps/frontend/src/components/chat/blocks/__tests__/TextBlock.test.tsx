/**
 * @file TextBlock.test.tsx
 * Tests for the TextBlock markdown rendering component.
 */

import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import { describe, expect, test } from 'vitest';

import type { TextBlock as TextBlockType } from '../../../../types/Chat';
import { TextBlock } from '../TextBlock';

describe('TextBlock', () => {
  test('renders plain text content', () => {
    const block: TextBlockType = {
      type: 'text',
      text: 'Hello, world!',
    };

    render(<TextBlock block={block} />);

    expect(screen.getByText('Hello, world!')).toBeInTheDocument();
  });

  test('renders markdown bold text', () => {
    const block: TextBlockType = {
      type: 'text',
      text: 'This is **bold** text',
    };

    render(<TextBlock block={block} />);

    const boldElement = screen.getByText('bold');
    expect(boldElement.tagName).toBe('STRONG');
  });

  test('renders markdown italic text', () => {
    const block: TextBlockType = {
      type: 'text',
      text: 'This is *italic* text',
    };

    render(<TextBlock block={block} />);

    const italicElement = screen.getByText('italic');
    expect(italicElement.tagName).toBe('EM');
  });

  test('renders markdown links', () => {
    const block: TextBlockType = {
      type: 'text',
      text: 'Check out [this link](https://example.com)',
    };

    render(<TextBlock block={block} />);

    const linkElement = screen.getByRole('link', { name: 'this link' });
    expect(linkElement).toHaveAttribute('href', 'https://example.com');
  });

  test('renders markdown lists', () => {
    const block: TextBlockType = {
      type: 'text',
      text: '- Item 1\n- Item 2\n- Item 3',
    };

    render(<TextBlock block={block} />);

    expect(screen.getByRole('list')).toBeInTheDocument();
    expect(screen.getByText('Item 1')).toBeInTheDocument();
    expect(screen.getByText('Item 2')).toBeInTheDocument();
    expect(screen.getByText('Item 3')).toBeInTheDocument();
  });

  test('renders inline code', () => {
    const block: TextBlockType = {
      type: 'text',
      text: 'Use the `console.log()` function',
    };

    render(<TextBlock block={block} />);

    const codeElement = screen.getByText('console.log()');
    expect(codeElement.tagName).toBe('CODE');
  });

  test('renders GFM strikethrough', () => {
    const block: TextBlockType = {
      type: 'text',
      text: 'This is ~~strikethrough~~ text',
    };

    render(<TextBlock block={block} />);

    const strikeElement = screen.getByText('strikethrough');
    expect(strikeElement.tagName).toBe('DEL');
  });

  test('applies prose styling classes', () => {
    const block: TextBlockType = {
      type: 'text',
      text: 'Styled content',
    };

    const { container } = render(<TextBlock block={block} />);

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain('prose');
  });

  test('handles empty text gracefully', () => {
    const block: TextBlockType = {
      type: 'text',
      text: '',
    };

    const { container } = render(<TextBlock block={block} />);

    // Should render without crashing
    expect(container.firstChild).toBeInTheDocument();
  });
});
