import { useCallback, useEffect, useRef, useState } from 'react';
import { logger } from '../lib/logger';
import { generateImageThumbnail } from '../utils/generateImageThumbnail';

export interface ImageSelectionOptions {
  perFileLimit?: number; // bytes
  combinedSizeLimit?: number; // bytes
  onError?: (message: string | null) => void;
}

export interface UseImageSelectionResult {
  selectedFiles: File[];
  previews: string[]; // object URLs (thumbnail or original)
  totalSize: number; // bytes
  totalSizeMiB: string; // formatted string
  processSelectedFiles: (
    incoming: File[],
    clearInput?: HTMLInputElement | null
  ) => void;
  removeFile: (index: number) => void;
  clearAll: () => void;
}

// Defaults mirror AddByPhotoModal constants
const DEFAULT_PER_FILE_LIMIT = 8 * 1024 * 1024; // 8 MiB
const DEFAULT_COMBINED_LIMIT = 20 * 1024 * 1024; // 20 MiB

export function useImageSelection(
  options?: ImageSelectionOptions
): UseImageSelectionResult {
  const perFileLimit = options?.perFileLimit ?? DEFAULT_PER_FILE_LIMIT;
  const combinedSizeLimit =
    options?.combinedSizeLimit ?? DEFAULT_COMBINED_LIMIT;
  const onError = options?.onError;

  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const previewsRef = useRef<string[]>([]);

  const reportError = useCallback(
    (msg: string | null) => {
      if (onError) onError(msg);
      if (msg) logger.debug('useImageSelection error:', msg);
    },
    [onError]
  );

  const revokeUrlSafe = (url: string) => {
    try {
      if (
        typeof (URL as any) !== 'undefined' &&
        typeof (URL as any).revokeObjectURL === 'function'
      ) {
        // @ts-ignore
        URL.revokeObjectURL(url);
      }
    } catch {
      /* ignore */
    }
  };

  const createPreviewForFile = async (f: File): Promise<string> => {
    try {
      const thumbBlob = await generateImageThumbnail(f, 150);
      if (thumbBlob) {
        if (
          typeof (URL as any) !== 'undefined' &&
          typeof (URL as any).createObjectURL === 'function'
        ) {
          // @ts-ignore
          return URL.createObjectURL(thumbBlob);
        }
      }
    } catch {
      // ignore and fall back
    }
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
    return `blob:${f.name}`; // deterministic fallback for tests
  };

  const processSelectedFiles = useCallback(
    (incoming: File[], clearInput?: HTMLInputElement | null) => {
      logger.debug(
        'useImageSelection processSelectedFiles',
        incoming.map((f) => f.name)
      );

      if (incoming.length === 0) {
        if (clearInput) clearInput.value = '';
        return;
      }

      const allFiles = [...selectedFiles, ...incoming];

      // Validate type
      const invalid = allFiles.filter((f) => !f.type.startsWith('image/'));
      if (invalid.length) {
        reportError(
          `Please select only image files. Invalid: ${invalid.map((f) => f.name).join(', ')}`
        );
        if (clearInput) clearInput.value = '';
        return;
      }

      // Per file size
      const oversized = allFiles.filter((f) => f.size > perFileLimit);
      if (oversized.length) {
        const maxMiB = (perFileLimit / (1024 * 1024)).toFixed(0);
        reportError(
          `File size too large. Max ${maxMiB} MiB per file. Oversized: ${oversized.map((f) => `${f.name} (${(f.size / (1024 * 1024)).toFixed(2)} MiB)`).join(', ')}`
        );
        if (clearInput) clearInput.value = '';
        return;
      }

      // Combined size
      const totalSize = allFiles.reduce((sum, f) => sum + f.size, 0);
      if (totalSize > combinedSizeLimit) {
        const maxTotalMiB = (combinedSizeLimit / (1024 * 1024)).toFixed(0);
        const currentTotalMiB = (totalSize / (1024 * 1024)).toFixed(2);
        reportError(
          `Combined file size (${currentTotalMiB} MiB) exceeds limit of ${maxTotalMiB} MiB. Please select fewer or smaller files.`
        );
        if (clearInput) clearInput.value = '';
        return;
      }

      // Build previews in parallel only for incoming new files
      (async () => {
        try {
          const created = await Promise.all(
            incoming.map((f) => createPreviewForFile(f))
          );
          previewsRef.current = [...previewsRef.current, ...created];
          setPreviews((prev) => [...prev, ...created]);
        } catch (err) {
          logger.debug('useImageSelection preview creation failure', err);
        }
      })();

      setSelectedFiles(allFiles);
      reportError(null);
      if (clearInput) clearInput.value = '';
    },
    [selectedFiles, perFileLimit, combinedSizeLimit, reportError]
  );

  const removeFile = useCallback((index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
    setPreviews((prev) => {
      const url = prev[index];
      if (url) revokeUrlSafe(url);
      const next = prev.filter((_, i) => i !== index);
      previewsRef.current = next.slice();
      return next;
    });
  }, []);

  const clearAll = useCallback(() => {
    previewsRef.current.forEach(revokeUrlSafe);
    previewsRef.current = [];
    setPreviews([]);
    setSelectedFiles([]);
  }, []);

  // Cleanup object URLs on unmount
  useEffect(() => {
    return () => {
      previewsRef.current.forEach(revokeUrlSafe);
      previewsRef.current = [];
    };
  }, []);

  const totalSize = selectedFiles.reduce((sum, f) => sum + f.size, 0);
  const totalSizeMiB = (totalSize / (1024 * 1024)).toFixed(2);

  return {
    selectedFiles,
    previews,
    totalSize,
    totalSizeMiB,
    processSelectedFiles,
    removeFile,
    clearAll,
  };
}
