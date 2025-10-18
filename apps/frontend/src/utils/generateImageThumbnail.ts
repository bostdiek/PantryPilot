export async function generateImageThumbnail(
  file: File,
  maxSize = 150
): Promise<Blob | null> {
  // Create an image bitmap if available for better performance
  try {
    const img = await createImageBitmap(file);
    const { width, height } = img;
    const scale = Math.min(1, maxSize / Math.max(width, height));
    const w = Math.max(1, Math.round(width * scale));
    const h = Math.max(1, Math.round(height * scale));

    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;
    ctx.drawImage(img, 0, 0, w, h);
    // Release ImageBitmap GPU resources as soon as possible
    try {
      // ImageBitmap.close may not exist in all environments; guard defensively
      // @ts-ignore
      if (typeof img.close === 'function') img.close();
    } catch {
      /* ignore */
    }

    return await new Promise<Blob | null>((resolve) => {
      canvas.toBlob((blob) => resolve(blob), 'image/jpeg', 0.8);
    });
  } catch {
    // If anything fails (e.g., createImageBitmap not available in tests), return null
    return null;
  }
}
