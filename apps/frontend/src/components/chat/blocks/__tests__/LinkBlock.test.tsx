/**
 * @file LinkBlock.test.tsx
 * Tests for the LinkBlock component that renders clickable link cards.
 */

import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import { describe, expect, test } from 'vitest';

import type { LinkBlock as LinkBlockType } from '../../../../types/Chat';
import { LinkBlock } from '../LinkBlock';

describe('LinkBlock', () => {
  test('renders link with label and href', () => {
    const block: LinkBlockType = {
      type: 'link',
      label: 'Example Website',
      href: 'https://example.com/page',
    };

    render(<LinkBlock block={block} />);

    const linkElement = screen.getByRole('link', { name: /example website/i });
    expect(linkElement).toBeInTheDocument();
    expect(linkElement).toHaveAttribute('href', 'https://example.com/page');
  });

  test('extracts and displays domain from URL', () => {
    const block: LinkBlockType = {
      type: 'link',
      label: 'Recipe Page',
      href: 'https://cooking.nytimes.com/recipes/12345',
    };

    render(<LinkBlock block={block} />);

    expect(screen.getByText('cooking.nytimes.com')).toBeInTheDocument();
  });

  test('opens link in new tab with security attributes', () => {
    const block: LinkBlockType = {
      type: 'link',
      label: 'External Link',
      href: 'https://example.com',
    };

    render(<LinkBlock block={block} />);

    const linkElement = screen.getByRole('link');
    expect(linkElement).toHaveAttribute('target', '_blank');
    expect(linkElement).toHaveAttribute('rel', 'noopener noreferrer');
  });

  test('displays external link icon', () => {
    const block: LinkBlockType = {
      type: 'link',
      label: 'Test Link',
      href: 'https://example.com',
    };

    const { container } = render(<LinkBlock block={block} />);

    // Lucide icons render as SVG
    const svgIcon = container.querySelector('svg');
    expect(svgIcon).toBeInTheDocument();
  });

  test('handles invalid URL gracefully', () => {
    const block: LinkBlockType = {
      type: 'link',
      label: 'Invalid URL',
      href: 'not-a-valid-url',
    };

    render(<LinkBlock block={block} />);

    // Should display full href when URL parsing fails
    expect(screen.getByText('not-a-valid-url')).toBeInTheDocument();
  });

  test('truncates long labels', () => {
    const block: LinkBlockType = {
      type: 'link',
      label:
        'This is a very long label that should be truncated when rendered in the UI',
      href: 'https://example.com',
    };

    const { container } = render(<LinkBlock block={block} />);

    // Check that truncate class is applied
    const labelDiv = container.querySelector('.truncate');
    expect(labelDiv).toBeInTheDocument();
  });

  test('applies hover styles class', () => {
    const block: LinkBlockType = {
      type: 'link',
      label: 'Hover Test',
      href: 'https://example.com',
    };

    render(<LinkBlock block={block} />);

    const linkElement = screen.getByRole('link');
    expect(linkElement.className).toContain('hover:');
  });
});
