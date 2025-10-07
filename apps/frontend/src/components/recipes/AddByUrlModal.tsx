import { useState, type FC, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  extractRecipeFromUrl,
  extractRecipeStreamFetch,
  getDraftByIdOwner,
} from '../../api/endpoints/aiDrafts';
import { logger } from '../../lib/logger';
import { useRecipeStore } from '../../stores/useRecipeStore';
import type { SSEEvent } from '../../types/AIDraft';
import { ApiErrorImpl } from '../../types/api';
import { Button } from '../ui/Button';
import { Dialog } from '../ui/Dialog';
import { ErrorMessage } from '../ui/ErrorMessage';
import { Input } from '../ui/Input';

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
  const [abortController, setAbortController] =
    useState<AbortController | null>(null);

  const handleClose = () => {
    // Cancel any ongoing stream
    if (abortController) {
      abortController.abort();
      setAbortController(null);
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

    // Try streaming first using fetch-based approach (supports auth headers)
    if (useStreaming) {
      try {
        const controller = await extractRecipeStreamFetch(
          url,
          undefined,
          (event: SSEEvent) => {
            // Handle progress updates
            const message = getProgressMessage(event);
            if (message) {
              setProgressMessages((prev) => [...prev, message]);
            }
          },
          async (signedUrl: string, draftId: string) => {
            // Streaming returns draft_id only (no signed_url)
            // POST returns signed_url directly
            if (signedUrl) {
              // POST endpoint case - navigate to signed URL
              navigate(signedUrl);
            } else if (draftId) {
              // Streaming endpoint case - fetch draft and navigate to new recipe page
              try {
                const draft = await getDraftByIdOwner(draftId);
                // Set the draft in the store
                const { setFormFromSuggestion } = useRecipeStore.getState();
                setFormFromSuggestion(draft.payload);
                // Navigate to new recipe page with AI flag
                navigate('/recipes/new?ai=1');
              } catch (err) {
                logger.error('Failed to fetch draft after streaming:', err);
                setError('Failed to load extracted recipe. Please try again.');
                setIsLoading(false);
                return;
              }
            }
            handleClose();
          },
          (err: ApiErrorImpl) => {
            // Streaming failed, try fallback to POST
            logger.warn('Streaming failed, falling back to POST:', err);
            setProgressMessages((prev) => [
              ...prev,
              'Switching to fallback method...',
            ]);
            fallbackToPost();
          }
        );
        setAbortController(controller);
      } catch (err) {
        logger.error('Failed to establish streaming connection:', err);
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
      logger.error('POST extraction failed:', err);
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
            onChange={setUrl}
            placeholder="https://example.com/recipe"
            disabled={isLoading}
            required
          />
          <p className="mt-2 text-sm text-gray-500">
            Paste a URL from a recipe website to automatically extract the
            recipe details.
          </p>
        </div>

        {error && <ErrorMessage message={error} />}

        {isLoading && (
          <div className="rounded-md bg-blue-50 p-4">
            <div className="flex items-center space-x-3">
              <div className="h-5 w-5">
                <svg
                  className="h-5 w-5 animate-spin text-blue-600"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
                  />
                </svg>
              </div>
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
