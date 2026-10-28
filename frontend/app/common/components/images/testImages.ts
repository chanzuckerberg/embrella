import { ImageAsset, ImageRendition } from '@app/common/types/images';

/** An ImageAsset as the API returns it, e.g. testImage({ id: 'b', notes: 'cracked' }). */
export const testImage = (overrides: Partial<ImageAsset> = {}): ImageAsset => {
  const id = overrides.id ?? 'a';
  const base = `/images/v1/images/${id}/file/`;

  return {
    id,
    notes: '',
    original_name: `${id}.png`,
    content_type: 'image/png',
    size_bytes: 1024,
    width: 1920,
    height: 1080,
    uploaded_by: 'jdoe',
    created_at: '2026-10-22T12:00:00Z',
    urls: {
      [ImageRendition.THUMB]: `${base}?r=thumb`,
      [ImageRendition.PREVIEW]: `${base}?r=preview`,
      [ImageRendition.ORIGINAL]: `${base}?r=original`,
    },
    ...overrides,
  };
};

export const pngFile = (name = 'shot.png', bytes = 10): File =>
  new File([new Uint8Array(bytes)], name, { type: 'image/png' });
