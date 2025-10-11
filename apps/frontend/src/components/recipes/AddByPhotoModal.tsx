import { useRef, useState, type ChangeEvent, type FC } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  extractRecipeFromImage,
  extractRecipeFromImageStream,
  getDraftByIdOwner,
} from '../../api/endpoints/aiDrafts';
import { logger } from '../../lib/logger';
import { useIsAuthenticated } from '../../stores/useAuthStore';
import { useRecipeStore } from '../../stores/useRecipeStore';
import type { SSEEvent } from '../../types/AIDraft';
import { ApiErrorImpl } from '../../types/api';
import { Button } from '../ui/Button';
import { Dialog } from '../ui/Dialog';
import { ErrorMessage } from '../ui/ErrorMessage';

interface AddByPhotoModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AddByPhotoModal: FC<AddByPhotoModalProps> = ({
  isOpen,
  onClose,
}) => {
  const navigate = useNavigate();
  const isAuthenticated = useIsAuthenticated();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
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
    setSelectedFile(null);
    setError(null);
    setProgressMessages([]);
    setIsLoading(false);
    onClose();
  };

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) {
      return;
    }

    // Validate file type
    if (!file.type.startsWith('image/')) {
      setError('Please select an image file (JPEG, PNG, etc.)');
      return;
    }

    // Validate file size (e.g., max 10MB)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      setError('File size is too large. Please select an image under 10MB.');
      return;
    }

    setSelectedFile(file);
    setError(null);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }

    // Check authentication
    if (!isAuthenticated) {
      const currentPath = window.location.pathname;
      navigate(`/login?next=${encodeURIComponent(currentPath)}`);
      return;
    }

    setError(null);
    setProgressMessages([]);
    setIsLoading(true);

    // Try streaming first using fetch-based approach (supports auth headers)
    if (useStreaming) {
      try {
        const controller = await extractRecipeFromImageStream(
          selectedFile,
          (event: SSEEvent) => {
            // Update progress messages
            if (event.detail) {
              setProgressMessages((prev) => [...prev, event.detail!]);
            }
          },
          async (signedUrl: string, draftId: string) => {
            logger.debug(
              'Stream complete, draft_id:',
              draftId,
              'signed_url:',
              signedUrl
            );

            if (signedUrl) {
              // Use the signed URL from the upload response
              navigate(signedUrl);
              handleClose();
            } else {
              // Fallback: fetch the draft using owner-only endpoint
              try {
                const draftResponse = await getDraftByIdOwner(draftId);
                logger.debug('Draft fetched:', draftResponse);

                // Set the form suggestion in the store
                const { setFormFromSuggestion } = useRecipeStore.getState();
                setFormFromSuggestion(draftResponse.payload);

                // Navigate to new recipe page with ai=1 flag to show AI indicator
                navigate(`/recipes/new?ai=1&draftId=${draftId}`);
                handleClose();
              } catch (err) {
                logger.error('Failed to fetch draft after streaming:', err);
                setError(
                  'Recipe extracted but failed to load. Please try again.'
                );
                setIsLoading(false);
              }
            }
          },
          (err: ApiErrorImpl) => {
            logger.error('Stream extraction error:', err);
            setError(err.message || 'Failed to extract recipe from image');
            setIsLoading(false);
          }
        );

        setAbortController(controller);
        return; // Success path - don't try fallback
      } catch (err) {
        logger.warn('Streaming failed, falling back to POST:', err);
        // Fall through to POST fallback
      }
    }

    // Fallback to POST request
    try {
      logger.debug('Using POST fallback for image extraction');
      const response = await extractRecipeFromImage(selectedFile);
      logger.debug('POST extraction response:', response);

      // Navigate to the signed URL
      if (response.signed_url) {
        navigate(response.signed_url);
        handleClose();
      } else {
        setError('Invalid response from server');
      }
    } catch (err) {
      logger.error('POST extraction error:', err);
      if (err instanceof ApiErrorImpl) {
        setError(err.message);
      } else {
        setError('Failed to extract recipe from image');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleButtonClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <Dialog isOpen={isOpen} onClose={handleClose} title="Upload Recipe Photo">
      <div className="space-y-4">
        {/* File input (hidden, triggered by button) */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleFileSelect}
          className="hidden"
          disabled={isLoading}
        />

        {/* Instructions */}
        <div className="space-y-2">
          <p className="text-sm text-gray-700">
            Take a photo or select an image of a recipe to automatically extract
            the recipe details.
          </p>
          <div className="rounded-md bg-blue-50 p-3">
            <p className="text-xs text-blue-800">
              <strong>Tip:</strong> For best results, ensure the recipe text is
              clear and well-lit. Works with recipe cards, cookbook pages, or
              screenshots.
            </p>
          </div>
        </div>

        {/* File selection button */}
        {!selectedFile ? (
          <Button
            variant="primary"
            onClick={handleButtonClick}
            disabled={isLoading}
            className="w-full"
          >
            📷 Select Photo
          </Button>
        ) : (
          <div className="rounded-md border border-gray-200 bg-gray-50 p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <svg
                  className="h-5 w-5 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                  />
                </svg>
                <div className="text-sm">
                  <p className="font-medium text-gray-900">
                    {selectedFile.name}
                  </p>
                  <p className="text-gray-500">
                    {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              </div>
              {!isLoading && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedFile(null)}
                >
                  Change
                </Button>
              )}
            </div>
          </div>
        )}

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
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-blue-900">
                  Extracting recipe from image...
                </p>
                {progressMessages.length > 0 && (
                  <div className="mt-2 max-h-32 space-y-1 overflow-y-auto">
                    {progressMessages.map((msg, idx) => (
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

        {/* Action buttons */}
        <div className="flex justify-end space-x-2 pt-4">
          <Button variant="ghost" onClick={handleClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleUpload}
            disabled={!selectedFile || isLoading}
          >
            {isLoading ? 'Processing...' : 'Extract Recipe'}
          </Button>
        </div>
      </div>
    </Dialog>
  );
};
