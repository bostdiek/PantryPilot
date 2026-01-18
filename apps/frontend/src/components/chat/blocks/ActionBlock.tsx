/**
 * ActionBlock component for rendering action approval UI.
 *
 * Displays an action proposal with Accept/Cancel buttons.
 * Used for tool confirmation workflows.
 */

import { Check, Loader2, X } from 'lucide-react';
import { useState } from 'react';

import type { ActionBlock as ActionBlockType } from '../../../types/Chat';
import { Button } from '../../ui/Button';

interface ActionBlockProps {
  block: ActionBlockType;
  onAccept?: (actionId: string) => Promise<void>;
  onCancel?: (actionId: string) => Promise<void>;
}

export type ActionStatus =
  | 'pending'
  | 'accepting'
  | 'canceling'
  | 'accepted'
  | 'canceled';

/**
 * Renders an action block with Accept/Cancel buttons.
 */
export function ActionBlock({ block, onAccept, onCancel }: ActionBlockProps) {
  const [status, setStatus] = useState<ActionStatus>('pending');

  const handleAccept = async () => {
    if (!onAccept) return;
    setStatus('accepting');
    try {
      await onAccept(block.action_id);
      setStatus('accepted');
    } catch {
      setStatus('pending');
    }
  };

  const handleCancel = async () => {
    if (!onCancel) return;
    setStatus('canceling');
    try {
      await onCancel(block.action_id);
      setStatus('canceled');
    } catch {
      setStatus('pending');
    }
  };

  const isLoading = status === 'accepting' || status === 'canceling';
  const isComplete = status === 'accepted' || status === 'canceled';

  return (
    <div className="my-2 rounded-lg border border-gray-200 bg-gray-50 p-3">
      <div className="mb-2 text-sm font-medium text-gray-700">
        {block.label}
      </div>

      {isComplete ? (
        <div
          className={`flex items-center gap-2 text-sm ${
            status === 'accepted' ? 'text-green-600' : 'text-gray-500'
          }`}
        >
          {status === 'accepted' ? (
            <>
              <Check className="h-4 w-4" />
              <span>Action accepted</span>
            </>
          ) : (
            <>
              <X className="h-4 w-4" />
              <span>Action canceled</span>
            </>
          )}
        </div>
      ) : (
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="primary"
            onClick={handleAccept}
            disabled={isLoading}
          >
            {status === 'accepting' ? (
              <>
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                Accepting...
              </>
            ) : (
              <>
                <Check className="mr-1 h-3 w-3" />
                Accept
              </>
            )}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={handleCancel}
            disabled={isLoading}
          >
            {status === 'canceling' ? (
              <>
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                Canceling...
              </>
            ) : (
              <>
                <X className="mr-1 h-3 w-3" />
                Cancel
              </>
            )}
          </Button>
        </div>
      )}
    </div>
  );
}
