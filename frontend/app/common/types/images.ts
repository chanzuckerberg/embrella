// Mirrors the backend images API (umbrella/images/serializers.py)

// Files served per image: WebP display copies plus the untouched original (download only)
export enum ImageRendition {
  THUMB = 'thumb',
  PREVIEW = 'preview',
  ORIGINAL = 'original',
}

// Named ImageAsset, not Image, to avoid clashing with next/image
export interface ImageAsset {
  id: string;
  notes: string;
  original_name: string;
  content_type: string;
  size_bytes: number;
  width: number;
  height: number;
  uploaded_by: string | null;
  created_at: string;
  // Paths relative to DJANGO_URL, e.g. { thumb: '/images/v1/images/<id>/file/?r=thumb', ... }
  urls: Record<ImageRendition, string>;
}

export enum UploadStatus {
  QUEUED = 'queued',
  UPLOADING = 'uploading',
  FAILED = 'failed',
}

// A file waiting for, or failing, upload. Successful uploads leave the queue.
export interface UploadItem {
  key: string;
  file: File;
  status: UploadStatus;
  progress: number; // 0–1
  error?: string;
}
