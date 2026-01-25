/**
 * TextBlock component for rendering markdown content from assistant messages.
 *
 * Uses react-markdown for safe, sanitized markdown rendering with
 * GitHub-flavored markdown support (tables, strikethrough, etc.).
 */

import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import type { TextBlock as TextBlockType } from '../../../types/Chat';

interface TextBlockProps {
  block: TextBlockType;
}

/**
 * Renders a text block with markdown support.
 * Uses Tailwind prose classes for consistent typography.
 */
export function TextBlock({ block }: TextBlockProps) {
  return (
    <div className="prose prose-sm prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-headings:my-2 prose-a:text-primary-600 prose-a:no-underline hover:prose-a:underline max-w-none">
      <Markdown remarkPlugins={[remarkGfm]}>{block.text}</Markdown>
    </div>
  );
}
