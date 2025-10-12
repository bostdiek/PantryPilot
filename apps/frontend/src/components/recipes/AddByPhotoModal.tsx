import { useRef, useState, type ChangeEvent, type FC } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  extractRecipeFromImage,
  extractRecipeFromImageStream,
  getDraftByIdOwner,
  isSafeInternalPath,
} from '../../api/endpoints/aiDrafts';
import { logger } from '../../lib/logger';
import { useIsAuthenticated } from '../../stores/useAuthStore';
import { useRecipeStore } from '../../stores/useRecipeStore';
import type { SSEEvent } from '../../types/AIDraft';
import { ApiErrorImpl } from '../../types/api';
import { Button } from '../ui/Button';
import { Dialog } from '../ui/Dialog';
import { ErrorMessage } from '../ui/ErrorMessage';

// Prefer streaming for better UX with progress updates, fallback to POST if unavailable
const USE_STREAMING = true;

// File size limits (matching backend constraints)
const PER_FILE_SIZE_LIMIT = 8 * 1024 * 1024; // 8 MiB per file
const COMBINED_SIZE_LIMIT = 20 * 1024 * 1024; // 20 MiB total

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
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progressMessages, setProgressMessages] = useState<string[]>([]);
  const [abortController, setAbortController] =
    useState<AbortController | null>(null);

  const handleClose = () => {
    // Cancel any ongoing stream
    if (abortController) {
      abortController.abort();
      setAbortController(null);
    }
    setSelectedFiles([]);
    setError(null);
    setProgressMessages([]);
    setIsLoading(false);
    onClose();
  };

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) {
      return;
    }

    // Validate file types
    const invalidFiles = files.filter((file) => !file.type.startsWith('image/'));
    if (invalidFiles.length > 0) {
      setError(
        `Please select only image files (JPEG, PNG, etc.). Invalid: ${invalidFiles.map((f) => f.name).join(', ')}`
      );
      return;
    }

    // Validate individual file sizes
    const oversizedFiles = files.filter(
      (file) => file.size > PER_FILE_SIZE_LIMIT
    );
    if (oversizedFiles.length > 0) {
      const maxSizeMiB = (PER_FILE_SIZE_LIMIT / (1024 * 1024)).toFixed(0);
      setError(
        `File size too large. Max ${maxSizeMiB} MiB per file. Oversized: ${oversizedFiles.map((f) => f.name).join(', ')}`
      );
      return;
    }

    // Validate combined file size
    const totalSize = files.reduce((sum, file) => sum + file.size, 0);
    if (totalSize > COMBINED_SIZE_LIMIT) {
      const maxTotalMiB = (COMBINED_SIZE_LIMIT / (1024 * 1024)).toFixed(0);
      const currentTotalMiB = (totalSize / (1024 * 1024)).toFixed(2);
      setError(
        `Combined file size (${currentTotalMiB} MiB) exceeds limit of ${maxTotalMiB} MiB. Please select fewer or smaller files.`
      );
      return;
    }

    setSelectedFiles(files);
    setError(null);
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      setError('Please select at least one file first');
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
    if (USE_STREAMING) {
      try {
        const controller = await extractRecipeFromImageStream(
          selectedFiles,
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

            // Validate signed URL before navigation for security
            if (signedUrl && isSafeInternalPath(signedUrl)) {
              // Use the signed URL from the upload response
              navigate(signedUrl);
              handleClose();
            } else if (signedUrl && !isSafeInternalPath(signedUrl)) {
              // Invalid or external URL - log warning and use fallback
              logger.warn(
                'Unsafe signed_url received, using fallback:',
                signedUrl
              );
              // Fallback to canonical internal path
              navigate(`/recipes/new?ai=1&draftId=${draftId}`);
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
      const response = await extractRecipeFromImage(selectedFiles);
      logger.debug('POST extraction response:', response);

      // Validate and navigate to the signed URL
      if (response.signed_url && isSafeInternalPath(response.signed_url)) {
        navigate(response.signed_url);
        handleClose();
      } else if (
        response.signed_url &&
        !isSafeInternalPath(response.signed_url)
      ) {
        // Invalid or external URL - log warning and use fallback
        logger.warn(
          'Unsafe signed_url received, using fallback:',
          response.signed_url
        );
        navigate(`/recipes/new?ai=1&draftId=${response.draft_id}`);
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

  const handleRemoveFile = (indexToRemove: number) => {
    setSelectedFiles((prev) => prev.filter((_, index) => index !== indexToRemove));
  };

  const handleClearAll = () => {
    setSelectedFiles([]);
  };

  // Calculate total size for display
  const totalSize = selectedFiles.reduce((sum, file) => sum + file.size, 0);
  const totalSizeMiB = (totalSize / (1024 * 1024)).toFixed(2);

  return (
    <Dialog isOpen={isOpen} onClose={handleClose} title="Upload Recipe Photo">
      <div className="space-y-4">
        {/* File input (hidden, triggered by button) */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          onChange={handleFileSelect}
          className="hidden"
          disabled={isLoading}
        />

        {/* Instructions */}
        <div className="space-y-2">
          <p className="text-sm text-gray-700">
            Select one or more images of a recipe to automatically extract the
            recipe details. You can upload multiple photos for multi-page recipes.
          </p>
          <div className="rounded-md bg-blue-50 p-3">
            <p className="text-xs text-blue-800">
              <strong>Tip:</strong> For best results, ensure the recipe text is
              clear and well-lit. Works with recipe cards, cookbook pages, or
              screenshots. Max 8 MiB per file, 20 MiB total.
            </p>
          </div>
        </div>

        {/* File selection button */}
        {selectedFiles.length === 0 ? (
          <Button
            variant="primary"
            onClick={handleButtonClick}
            disabled={isLoading}
            className="w-full"
          >
            📷 Select Photos
          </Button>
        ) : (
          <div className="space-y-3">
            {/* File list header with summary */}
            <div className="flex items-center justify-between rounded-md border border-gray-200 bg-gray-50 p-3">
              <div className="text-sm">
                <p className="font-medium text-gray-900">
                  {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} selected
                </p>
                <p className="text-gray-500">
                  Total: {totalSizeMiB} MiB
                </p>
              </div>
              {!isLoading && (
                <div className="flex space-x-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleButtonClick}
                  >
                    Add More
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleClearAll}
                  >
                    Clear All
                  </Button>
                </div>
              )}
            </div>

            {/* File list */}
            <div className="max-h-60 space-y-2 overflow-y-auto">
              {selectedFiles.map((file, index) => (
                <div
                  key={`${file.name}-${index}`}
                  className="flex items-center justify-between rounded-md border border-gray-200 bg-white p-2"
                >
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
                        {index + 1}. {file.name}
                      </p>
                      <p className="text-gray-500">
                        {(file.size / (1024 * 1024)).toFixed(2)} MiB
                      </p>
                    </div>
                  </div>
                  {!isLoading && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemoveFile(index)}
                      aria-label={`Remove ${file.name}`}
                    >
                      ✕
                    </Button>
                  )}
                </div>
              ))}
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
            disabled={selectedFiles.length === 0 || isLoading}
          >
            {isLoading ? 'Processing...' : 'Extract Recipe'}
          </Button>
        </div>
      </div>
    </Dialog>
  );
};
