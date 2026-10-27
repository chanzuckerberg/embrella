import { API, DJANGO_URL } from '@app/common/constants/api';
import {
  deleteResource,
  fetchResource,
  patchResource,
  postFormDataWithProgress,
  putResource,
} from '@app/common/queries/fetchResource';
import { ImageAsset, ImageRendition } from '@app/common/types/images';

const HTTP_PAYLOAD_TOO_LARGE = 413;

const gridImagesUrl = (gridId: number): string => `${DJANGO_URL}${API.GRID_IMAGES.replace('grid_id', String(gridId))}`;

/** Absolute URL of one of an image's files, e.g. for <img src>. */
export const imageSrc = (image: ImageAsset, rendition: ImageRendition): string =>
  `${DJANGO_URL}${image.urls[rendition]}`;

export async function listGridImages(gridId: number): Promise<ImageAsset[]> {
  const response = await fetchResource(gridImagesUrl(gridId));
  if (!response.ok) {
    throw new Error('Failed to load images');
  }

  return response.json();
}

/** Upload one file to a grid. Throws with the server's message, e.g. "Save a single page." */
export async function uploadGridImage(
  gridId: number,
  file: File,
  onProgress: (fraction: number) => void
): Promise<ImageAsset> {
  const form = new FormData();
  form.append('file', file);

  const result = await postFormDataWithProgress(gridImagesUrl(gridId), form, onProgress);
  if (!result.ok) {
    throw new Error(errorMessage(result.status, result.body));
  }

  return JSON.parse(result.body);
}

export async function updateImageNotes(imageId: string, notes: string): Promise<ImageAsset> {
  const response = await patchResource(`${DJANGO_URL}${API.IMAGE.replace('image_id', imageId)}`, { notes });
  if (!response.ok) {
    throw new Error(errorMessage(response.status, await response.text()));
  }

  return response.json();
}

export async function deleteGridImage(gridId: number, imageId: string): Promise<void> {
  const path = API.GRID_IMAGE.replace('grid_id', String(gridId)).replace('image_id', imageId);
  const response = await deleteResource(`${DJANGO_URL}${path}`);
  if (!response.ok) {
    throw new Error(errorMessage(response.status, await response.text()));
  }
}

/** Save a grid's image order. ``imageIds`` must be all of its images, else the server answers 409. */
export async function reorderGridImages(gridId: number, imageIds: string[]): Promise<ImageAsset[]> {
  const path = API.GRID_IMAGES_ORDER.replace('grid_id', String(gridId));
  const response = await putResource(`${DJANGO_URL}${path}`, { image_ids: imageIds });
  if (!response.ok) {
    throw new Error(errorMessage(response.status, await response.text()));
  }

  return response.json();
}

/**
 * DRF errors arrive as {"detail": "..."} or, from validation, {"field": ["..."]};
 * nginx's 413 is an HTML page.
 */
function errorMessage(status: number, body: string): string {
  if (status === HTTP_PAYLOAD_TOO_LARGE) {
    return 'File is too large.';
  }

  try {
    const parsed = JSON.parse(body) as Record<string, unknown>;
    const message = parsed.detail ?? Object.values(parsed).flat()[0];
    if (typeof message === 'string') {
      return message;
    }
  } catch {
    /* not JSON */
  }

  return `Something went wrong (${status}). Please try again.`;
}
