import { useEffect, useRef, useState, type ChangeEvent, type FC } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  extractRecipeFromImage,
  extractRecipeFromImageStream,
  getDraftByIdOwner,
  isSafeInternalPath,
} from '../../api/endpoints/aiDrafts';
import { useIsMobile } from '../../hooks/useMediaQuery';
import { logger } from '../../lib/logger';
import { useIsAuthenticated } from '../../stores/useAuthStore';
import { useRecipeStore } from '../../stores/useRecipeStore';
import type { SSEEvent } from '../../types/AIDraft';
import { ApiErrorImpl } from '../../types/api';
import { generateImageThumbnail } from '../../utils/generateImageThumbnail';
import { Button } from '../ui/Button';
import { Dialog } from '../ui/Dialog';
import { ErrorMessage } from '../ui/ErrorMessage';
import ImageThumbnail from './ImageThumbnail';

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
  const isMobile = useIsMobile();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  // Desktop camera stream state
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [showCameraPreview, setShowCameraPreview] = useState(false);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [inputSource, setInputSource] = useState<'camera' | 'file' | null>(
    null
  );
  const [filePreviews, setFilePreviews] = useState<string[]>([]);
  const previewsRef = useRef<string[]>([]);
  const [focusedThumbnailIndex, setFocusedThumbnailIndex] = useState<
    number | null
  >(null);
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

  const processSelectedFiles = (
    incomingFiles: File[],
    clearInput?: HTMLInputElement | null
  ) => {
    logger.debug(
      'processSelectedFiles called',
      incomingFiles.map((f) => f.name)
    );
    // Some browsers (and the testing environment) will ignore files that don't match
    // the input's `accept` attribute resulting in an empty FileList. In that case,
    // surface a helpful error for the user/tests instead of silently returning.
    if (incomingFiles.length === 0) {
      // If a file input was provided (clearInput), assume the user attempted to select
      // files but none matched the accept criteria -> show invalid file error.
      if (
        clearInput &&
        clearInput.accept &&
        clearInput.accept.includes('image')
      ) {
        setError('Please select only image files');
        if (clearInput) clearInput.value = '';
        return;
      }
      return;
    }

    // Merge with existing files for "Add More" functionality
    const allFiles = [...selectedFiles, ...incomingFiles];

    // Validate file types
    const invalidFiles = allFiles.filter(
      (file) => !file.type.startsWith('image/')
    );
    if (invalidFiles.length > 0) {
      logger.debug(
        'processSelectedFiles invalid files',
        invalidFiles.map((f) => f.name)
      );
      // Helpful console output during tests to ensure branch is hit
      // (left intentionally lightweight; removed after debugging if no longer needed)
      console.log(
        'AddByPhotoModal: invalid files detected',
        invalidFiles.map((f) => f.name)
      );
      setError(
        `Please select only image files. Invalid: ${invalidFiles.map((f) => f.name).join(', ')}`
      );
      if (clearInput) clearInput.value = '';
      return;
    }

    // Validate individual file sizes
    const oversizedFiles = allFiles.filter(
      (file) => file.size > PER_FILE_SIZE_LIMIT
    );
    if (oversizedFiles.length > 0) {
      const maxSizeMiB = (PER_FILE_SIZE_LIMIT / (1024 * 1024)).toFixed(0);
      setError(
        `File size too large. Max ${maxSizeMiB} MiB per file. Oversized: ${oversizedFiles
          .map((f) => `${f.name} (${(f.size / (1024 * 1024)).toFixed(2)} MiB)`)
          .join(', ')}`
      );
      if (clearInput) clearInput.value = '';
      return;
    }

    // Validate combined file size
    const totalSize = allFiles.reduce((sum, file) => sum + file.size, 0);
    if (totalSize > COMBINED_SIZE_LIMIT) {
      const maxTotalMiB = (COMBINED_SIZE_LIMIT / (1024 * 1024)).toFixed(0);
      const currentTotalMiB = (totalSize / (1024 * 1024)).toFixed(2);
      setError(
        `Combined file size (${currentTotalMiB} MiB) exceeds limit of ${maxTotalMiB} MiB. Please select fewer or smaller files.`
      );
      if (clearInput) clearInput.value = '';
      return;
    }

    // (previous safeCreateObjectURL removed - using generateImageThumbnail or URL.createObjectURL directly)

    // Create thumbnails (resize) when possible to reduce memory and bandwidth
    const createPreviewForFile = async (f: File): Promise<string> => {
      try {
        const thumbBlob = await generateImageThumbnail(f, 150);
        if (thumbBlob) {
          if (
            typeof (URL as any) !== 'undefined' &&
            typeof (URL as any).createObjectURL === 'function'
          ) {
            // @ts-ignore - URL.createObjectURL exists in browsers
            return URL.createObjectURL(thumbBlob);
          }
        }
      } catch {
        // ignore and fall back
      }

      // Fallback to original file object URL or deterministic string for tests
      try {
        if (
          typeof (URL as any) !== 'undefined' &&
          typeof (URL as any).createObjectURL === 'function'
        ) {
          // @ts-ignore
          return URL.createObjectURL(f);
        }
      } catch {
        // ignore
      }
      return `blob:${f.name}`;
    };

    // Build previews async for incomingFiles and append once ready
    (async () => {
      const created: string[] = [];
      for (const f of incomingFiles) {
        const url = await createPreviewForFile(f);
        created.push(url);
      }
      previewsRef.current = [...previewsRef.current, ...created];
      setFilePreviews((prev) => [...prev, ...created]);
    })();

    setSelectedFiles(allFiles);
    setError(null);
    if (clearInput) clearInput.value = '';
  };

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    setInputSource('file');
    const incomingFiles = Array.from(e.target.files || []);
    // Debugging: log incoming file details to help tests
    console.log(
      'handleFileSelect incomingFiles',
      incomingFiles.map((f) => ({ name: f.name, type: f.type }))
    );
    if (incomingFiles.length === 0) {
      setError('Please select only image files');
      if (e.currentTarget) e.currentTarget.value = '';
      return;
    }
    processSelectedFiles(incomingFiles, e.currentTarget);
  };

  const handleCameraCapture = (e: ChangeEvent<HTMLInputElement>) => {
    setInputSource('camera');
    const incomingFiles = Array.from(e.target.files || []);
    if (incomingFiles.length === 0) {
      // Align with tests which simulate empty selection
      setError('Please select at least one file');
      return;
    }
    processSelectedFiles(incomingFiles, e.currentTarget);
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

  const handleCameraButtonClick = () => {
    // On mobile, prefer the capture input which triggers device camera
    if (isMobile) {
      cameraInputRef.current?.click();
      return;
    }

    // On desktop, if getUserMedia is available, open in-modal camera preview
    const md = (navigator as any).mediaDevices;
    if (md && typeof md.getUserMedia === 'function') {
      setShowCameraPreview(true);
      // Start stream asynchronously when preview shown via effect
      return;
    }

    // Fallback to file chooser if no camera available
    cameraInputRef.current?.click();
  };

  // Start/stop media stream when preview is shown/hidden
  useEffect(() => {
    let mounted = true;
    const v = videoRef.current;
    async function start() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment' },
          audio: false,
        });
        mediaStreamRef.current = stream;
        if (!mounted) return;
        if (v) {
          // @ts-ignore - srcObject exists on HTMLVideoElement
          (v as any).srcObject = stream;
          // Autoplay may be blocked; try play()
          try {
            await v.play();
          } catch {
            /* ignore */
          }
        }
      } catch (err) {
        // If permission denied or no camera, fall back to file input and show error
        logger.debug('getUserMedia error', err);
        setError(
          'Unable to access camera. Please allow camera permissions or use file picker.'
        );
        setShowCameraPreview(false);
      }
    }

    if (showCameraPreview) start();

    return () => {
      mounted = false;
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((t) => t.stop());
        mediaStreamRef.current = null;
      }
      if (v) {
        try {
          // detach stream
          (v as any).srcObject = null;
        } catch {
          /* ignore */
        }
      }
    };
  }, [showCameraPreview]);

  const handleCaptureFromPreview = async () => {
    const video = videoRef.current;
    if (!video || !mediaStreamRef.current) {
      setError('Camera is not available');
      return;
    }

    // Draw current video frame to canvas and convert to blob
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      setError('Unable to capture image');
      return;
    }
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob((b) => resolve(b), 'image/jpeg', 0.9)
    );
    if (!blob) {
      setError('Failed to capture image');
      return;
    }

    // Create a File from the blob so downstream logic expects File objects
    const file = new File([blob], `camera-${Date.now()}.jpg`, {
      type: 'image/jpeg',
    });
    // Stop preview and stream
    setShowCameraPreview(false);
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    }

    // Pass to existing processing path
    processSelectedFiles([file], null);
  };

  const handleRemoveFile = (indexToRemove: number) => {
    setSelectedFiles((prev) =>
      prev.filter((_, index) => index !== indexToRemove)
    );
    // Revoke and remove corresponding preview
    setFilePreviews((prev) => {
      const url = prev[indexToRemove];
      if (url) {
        try {
          if (
            typeof (URL as any) !== 'undefined' &&
            typeof (URL as any).revokeObjectURL === 'function'
          ) {
            // @ts-ignore
            URL.revokeObjectURL(url);
          }
        } catch {
          // ignore
        }
      }
      const next = prev.filter((_, i) => i !== indexToRemove);
      previewsRef.current = next.slice();
      return next;
    });
  };

  const handleClearAll = () => {
    // Revoke all previews
    previewsRef.current.forEach((url) => {
      try {
        if (
          typeof (URL as any) !== 'undefined' &&
          typeof (URL as any).revokeObjectURL === 'function'
        ) {
          // @ts-ignore
          URL.revokeObjectURL(url);
        }
      } catch {
        // ignore
      }
    });
    previewsRef.current = [];
    setFilePreviews([]);
    setSelectedFiles([]);
  };

  // Cleanup object URLs on unmount
  useEffect(() => {
    return () => {
      previewsRef.current.forEach((url) => {
        try {
          if (
            typeof (URL as any) !== 'undefined' &&
            typeof (URL as any).revokeObjectURL === 'function'
          ) {
            // @ts-ignore
            URL.revokeObjectURL(url);
          }
        } catch {
          // ignore
        }
      });
      previewsRef.current = [];
    };
  }, []);

  // Calculate total size for display
  const totalSize = selectedFiles.reduce((sum, file) => sum + file.size, 0);
  const totalSizeMiB = (totalSize / (1024 * 1024)).toFixed(2);

  return (
    <Dialog
      isOpen={isOpen}
      onClose={handleClose}
      title="Upload Recipe Photo"
      data-input-source={inputSource ?? undefined}
    >
      <div className="space-y-4">
        {/* File input (hidden, triggered by button) */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          aria-label="Choose files"
          onChange={handleFileSelect}
          className="hidden"
          disabled={isLoading}
        />

        {/* Camera input (hidden) - capture attribute restores mobile camera access */}
        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleCameraCapture}
          className="hidden"
          disabled={isLoading}
        />

        {/* Instructions */}
        <div className="space-y-2">
          <p className="text-sm text-gray-700">
            Select one or more images of a recipe to automatically extract the
            recipe details. You can upload multiple photos for multi-page
            recipes.
          </p>
          <div className="rounded-md bg-blue-50 p-3">
            <p className="text-xs text-blue-800">
              <strong>Tip:</strong> For best results, ensure the recipe text is
              clear and well-lit. Works with recipe cards, cookbook pages, or
              screenshots. Max 8 MiB per file, 20 MiB total.
            </p>
          </div>
        </div>

        {/* File selection buttons (camera + file chooser) */}
        {selectedFiles.length === 0 ? (
          <div
            className={`${
              isMobile ? 'flex flex-col gap-2' : 'grid grid-cols-2 gap-2'
            }`}
          >
            <Button
              variant="primary"
              onClick={handleCameraButtonClick}
              disabled={isLoading}
              className="min-h-[48px] w-full min-w-[48px] text-lg"
              aria-label="Take photo with camera"
            >
              📷 Take Photo
            </Button>
            <Button
              variant="secondary"
              onClick={handleButtonClick}
              disabled={isLoading}
              className="min-h-[48px] w-full min-w-[48px] text-lg"
              aria-label="Open file chooser"
            >
              📁 Browse Files
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {/* File list header with summary */}
            <div className="flex items-center justify-between rounded-md border border-gray-200 bg-gray-50 p-3">
              <div className="text-sm">
                <p className="font-medium text-gray-900">
                  {selectedFiles.length} file
                  {selectedFiles.length !== 1 ? 's' : ''} selected
                </p>
                <p className="text-gray-500">Total: {totalSizeMiB} MiB</p>
              </div>
              {!isLoading && (
                <div className="flex space-x-2">
                  <Button variant="ghost" size="sm" onClick={handleButtonClick}>
                    Add More
                  </Button>
                  <Button variant="ghost" size="sm" onClick={handleClearAll}>
                    Clear All
                  </Button>
                </div>
              )}
            </div>

            {/* Textual list of filenames (kept for accessibility/tests) */}
            <div className="mt-2 space-y-1 text-sm text-gray-700">
              {selectedFiles.map((file, idx) => (
                <p
                  key={`name-${file.name}-${idx}`}
                >{`${idx + 1}. ${file.name}`}</p>
              ))}
            </div>

            {/* Thumbnail grid */}
            <div
              role="list"
              aria-label="Selected images"
              className="grid grid-cols-2 gap-3 p-1 sm:grid-cols-3 md:grid-cols-4"
              onKeyDown={(e) => {
                if (focusedThumbnailIndex === null) return;
                const cols =
                  window.innerWidth >= 768
                    ? 4
                    : window.innerWidth >= 640
                      ? 3
                      : 2;
                let next = focusedThumbnailIndex;
                if (e.key === 'ArrowRight')
                  next = Math.min(
                    selectedFiles.length - 1,
                    focusedThumbnailIndex + 1
                  );
                if (e.key === 'ArrowLeft')
                  next = Math.max(0, focusedThumbnailIndex - 1);
                if (e.key === 'ArrowDown')
                  next = Math.min(
                    selectedFiles.length - 1,
                    focusedThumbnailIndex + cols
                  );
                if (e.key === 'ArrowUp')
                  next = Math.max(0, focusedThumbnailIndex - cols);
                if (next !== focusedThumbnailIndex) {
                  e.preventDefault();
                  setFocusedThumbnailIndex(next);
                }
              }}
              onTouchStart={(e) => {
                // Basic swipe gesture for mobile: left/right to change focus
                const touch = e.touches?.[0];
                if (!touch) return;
                (window as any)._swipeStartX = touch.clientX;
              }}
              onTouchEnd={(e) => {
                const touch = e.changedTouches?.[0];
                if (!touch || focusedThumbnailIndex === null) return;
                const startX = (window as any)._swipeStartX;
                const deltaX = touch.clientX - startX;
                if (Math.abs(deltaX) > 30) {
                  let next = focusedThumbnailIndex;
                  if (deltaX < 0)
                    next = Math.min(
                      selectedFiles.length - 1,
                      focusedThumbnailIndex + 1
                    );
                  if (deltaX > 0) next = Math.max(0, focusedThumbnailIndex - 1);
                  if (next !== focusedThumbnailIndex)
                    setFocusedThumbnailIndex(next);
                }
              }}
            >
              {selectedFiles.map((file, index) => {
                const previewUrl = filePreviews[index] ?? null;
                const loading = !previewUrl;
                return (
                  <div
                    key={`${file.name}-${index}`}
                    role="listitem"
                    className="flex flex-col items-center"
                  >
                    <ImageThumbnail
                      src={previewUrl}
                      alt={file.name}
                      index={index}
                      selected={focusedThumbnailIndex === index}
                      onRemove={handleRemoveFile}
                      onFocusRequest={(i) => setFocusedThumbnailIndex(i)}
                      loading={loading}
                      error={false}
                    />
                    <div className="mt-1 text-center text-xs text-gray-500">
                      {(file.size / (1024 * 1024)).toFixed(2)} MiB
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Desktop camera preview overlay (in-modal) */}
        {showCameraPreview && (
          <div className="rounded-md border bg-gray-50 p-3">
            <p className="mb-2 text-sm font-medium">Camera Preview</p>
            <div className="flex w-full justify-center">
              <video
                ref={videoRef}
                className="w-full max-w-md rounded bg-black"
                playsInline
                muted
              />
            </div>
            <div className="mt-3 flex justify-end space-x-2">
              <Button
                variant="ghost"
                onClick={() => {
                  // Stop and close preview
                  setShowCameraPreview(false);
                  if (mediaStreamRef.current) {
                    mediaStreamRef.current.getTracks().forEach((t) => t.stop());
                    mediaStreamRef.current = null;
                  }
                }}
              >
                Cancel
              </Button>
              <Button variant="primary" onClick={handleCaptureFromPreview}>
                Capture Photo
              </Button>
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
