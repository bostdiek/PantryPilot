/**
 * LinkBlock component for rendering clickable link cards.
 *
 * Displays links as styled cards with the label and URL,
 * opening in a new tab for external links.
 */

import { ExternalLink } from 'lucide-react';

import type { LinkBlock as LinkBlockType } from '../../../types/Chat';

interface LinkBlockProps {
  block: LinkBlockType;
}

/**
 * Renders a link block as a styled card.
 */
export function LinkBlock({ block }: LinkBlockProps) {
  // Extract domain for display
  let displayUrl = block.href;
  try {
    const url = new URL(block.href);
    displayUrl = url.hostname;
  } catch {
    // Use full href if parsing fails
  }

  return (
    <a
      href={block.href}
      target="_blank"
      rel="noopener noreferrer"
      className="group hover:border-primary-300 hover:bg-primary-50 my-1 flex items-center gap-3 rounded-lg border border-gray-200 bg-white p-3 transition-colors"
    >
      <div className="min-w-0 flex-1">
        <div className="group-hover:text-primary-700 truncate font-medium text-gray-900">
          {block.label}
        </div>
        <div className="truncate text-xs text-gray-500">{displayUrl}</div>
      </div>
      <ExternalLink className="group-hover:text-primary-600 h-4 w-4 flex-shrink-0 text-gray-400" />
    </a>
  );
}
