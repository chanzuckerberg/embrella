// Mirrors umbrella/images/constants.py MAX_UPLOAD_BYTES (nginx client_max_body_size 100M)
export const MAX_UPLOAD_MB = 100;
export const MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024;

// File picker filter and client-side check; the server re-checks the actual bytes
export const ACCEPTED_IMAGE_TYPES: Record<string, string[]> = {
  'image/png': ['.png'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/webp': ['.webp'],
  'image/tiff': ['.tif', '.tiff'],
};

export const TOO_LARGE_MESSAGE = `File is larger than ${MAX_UPLOAD_MB} MB.`;
export const WRONG_TYPE_MESSAGE = 'Only PNG, JPEG, WebP or single-page TIFF images.';

// Carousel slide height; previews scale down to fit
export const PREVIEW_HEIGHT_PX = 360;

// Square thumbnail tiles; thumbs keep their aspect and are cropped by object-fit
export const THUMB_TILE_PX = 64;
