import { useState, type FC, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Dialog } from '../ui/Dialog';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { ErrorMessage } from '../ui/ErrorMessage';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import {
  extractRecipeStream,
  extractRecipeFromUrl,
} from '../../api/endpoints/aiDrafts';
import { ApiErrorImpl } from '../../types/api';
import type { SSEEvent } from '../../types/AIDraft';

interface AddByUrlModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AddByUrlModal: FC<AddByUrlModalProps> = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  const [url, setUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progressMessages, setProgressMessages] = useState<string[]>([]);
  const [useStreaming] = useState(true);
  const [eventSource, setEventSource] = useState<EventSource | null>(null);

  const handleClose = () => {
    // Cancel any ongoing SSE connection
    if (eventSource) {
      eventSource.close();
      setEventSource(null);
    }
    setUrl('');
    setError(null);
    setProgressMessages([]);
    setIsLoading(false);
    onClose();
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setProgressMessages([]);

    // Basic URL validation
    if (!url.trim()) {
      setError('Please enter a URL');
      return;
    }

    try {
      new URL(url);
    } catch {
      setError('Please enter a valid URL');
      return;
    }

    setIsLoading(true);

    // Try streaming first
    if (useStreaming) {
      try {
        const es = extractRecipeStream(
          url,
          undefined,
          (event: SSEEvent) => {
            // Handle progress updates
            const message = getProgressMessage(event);
            if (message) {
              setProgressMessages((prev) => [...prev, message]);
            }
          },
          (signedUrl: string) => {
            // Success! Navigate to the signed URL
            navigate(signedUrl);
            handleClose();
          },
          (err: ApiErrorImpl) => {
            // SSE failed, try fallback to POST
            console.warn('SSE failed, falling back to POST:', err);
            setProgressMessages((prev) => [
              ...prev,
              'Switching to fallback method...',
            ]);
            fallbackToPost();
          }
        );
        setEventSource(es);
      } catch (err) {
        console.error('Failed to establish SSE connection:', err);
        fallbackToPost();
      }
    } else {
      await fallbackToPost();
    }
  };

  const fallbackToPost = async () => {
    try {
      setProgressMessages((prev) => [...prev, 'Extracting recipe...']);
      const response = await extractRecipeFromUrl(url, undefined);

      // Navigate to the signed URL
      navigate(response.signed_url);
      handleClose();
    } catch (err) {
      console.error('POST extraction failed:', err);
      const apiError = err as ApiErrorImpl;
      setError(
        apiError.message || 'Failed to extract recipe. Please try again.'
      );
      setIsLoading(false);
    }
  };

  const getProgressMessage = (event: SSEEvent): string | null => {
    switch (event.status) {
      case 'started':
        return 'Starting extraction...';
      case 'fetching':
        return 'Fetching page content...';
      case 'ai_call':
        return 'Analyzing recipe with AI...';
      case 'converting':
        return 'Converting recipe data...';
      case 'complete':
        return event.success
          ? 'Recipe extracted successfully!'
          : 'Recipe extraction completed';
      case 'error':
        return null; // Error will be handled separately
      default:
        return event.detail || null;
    }
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={handleClose}
      title="Add Recipe from URL"
      size="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <Input
            label="Recipe URL"
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com/recipe"
            disabled={isLoading}
            required
          />
          <p className="mt-2 text-sm text-gray-500">
            Paste a URL from a recipe website to automatically extract the
            recipe details.
          </p>
        </div>

        {error && <ErrorMessage>{error}</ErrorMessage>}

        {isLoading && (
          <div className="rounded-md bg-blue-50 p-4">
            <div className="flex items-center space-x-3">
              <LoadingSpinner size="sm" />
              <div className="flex-1">
                <h4 className="text-sm font-medium text-blue-900">
                  Extracting recipe...
                </h4>
                {progressMessages.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {progressMessages.slice(-3).map((msg, idx) => (
                      <p key={idx} className="text-xs text-blue-700">
                        {msg}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        <div className="flex justify-end space-x-3">
          <Button
            type="button"
            variant="secondary"
            onClick={handleClose}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={isLoading}>
            {isLoading ? 'Extracting...' : 'Extract Recipe'}
          </Button>
        </div>
      </form>
    </Dialog>
  );
};
