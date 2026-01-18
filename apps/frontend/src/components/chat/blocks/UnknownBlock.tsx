/**
 * UnknownBlock component for graceful handling of unrecognized block types.
 *
 * Provides a fallback renderer for future block types that the current
 * frontend version doesn't know how to render.
 */

import { HelpCircle } from 'lucide-react';

import type { ChatContentBlock } from '../../../types/Chat';

interface UnknownBlockProps {
  block: ChatContentBlock;
}

/**
 * Renders an unknown block type with a helpful message.
 */
export function UnknownBlock({ block }: UnknownBlockProps) {
  return (
    <div className="my-1 flex items-center gap-2 rounded-lg border border-dashed border-gray-300 bg-gray-50 p-2 text-sm text-gray-500">
      <HelpCircle className="h-4 w-4 flex-shrink-0" />
      <span>
        Unsupported content type: <code className="text-xs">{block.type}</code>
      </span>
    </div>
  );
}
