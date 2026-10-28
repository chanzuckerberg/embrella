import { useCallback, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  deleteGridImage,
  listGridImages,
  reorderGridImages,
  updateImageNotes,
  uploadGridImage,
} from '@app/common/queries/imagesApi';
import { ImageAsset, UploadItem, UploadStatus } from '@app/common/types/images';

export const gridImagesKey = (gridId: number | null) => ['grid-images', gridId] as const;

/** A grid's images in display order. Shared by the dialog tab, thumb strip and grid logging tile. */
export const useGridImages = (gridId: number | null) =>
  useQuery({
    queryKey: gridImagesKey(gridId),
    queryFn: () => listGridImages(gridId as number),
    enabled: gridId !== null,
  });

/**
 * Upload queue for one grid. Files go one at a time so a batch doesn't tie up every
 * backend worker; each success refreshes the image list and leaves the queue.
 *
 *   add(files) ─► QUEUED ─► UPLOADING (progress) ─► done (removed) | FAILED (kept until dismissed)
 *
 * Remount per grid (key={gridId}) for a fresh queue. Queued files keep uploading after unmount.
 */
export function useGridImageUploads(gridId: number | null) {
  const queryClient = useQueryClient();
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const pending = useRef<UploadItem[]>([]);
  const isSending = useRef(false);
  const nextKey = useRef(0);

  const patch = useCallback((key: string, changes: Partial<UploadItem>) => {
    setUploads((prev) => prev.map((item) => (item.key === key ? { ...item, ...changes } : item)));
  }, []);

  const append = useCallback((items: Omit<UploadItem, 'key'>[]): UploadItem[] => {
    const keyed = items.map((item) => ({ ...item, key: String(nextKey.current++) }));
    setUploads((prev) => [...prev, ...keyed]);
    return keyed;
  }, []);

  const send = useCallback(
    async (item: UploadItem) => {
      patch(item.key, { status: UploadStatus.UPLOADING });
      try {
        await uploadGridImage(gridId as number, item.file, (progress) => patch(item.key, { progress }));
        setUploads((prev) => prev.filter((other) => other.key !== item.key));
        queryClient.invalidateQueries({ queryKey: gridImagesKey(gridId) });
      } catch (error) {
        patch(item.key, { status: UploadStatus.FAILED, error: (error as Error).message });
      }
    },
    [gridId, patch, queryClient]
  );

  // Drains the queue; a second call while sending just lets the running loop pick new files up
  const drain = useCallback(async () => {
    if (isSending.current || gridId === null) return;

    isSending.current = true;
    for (let item = pending.current.shift(); item; item = pending.current.shift()) {
      await send(item);
    }
    isSending.current = false;
  }, [gridId, send]);

  const add = useCallback(
    (files: File[]) => {
      pending.current.push(...append(files.map((file) => ({ file, status: UploadStatus.QUEUED, progress: 0 }))));
      void drain();
    },
    [append, drain]
  );

  // Rejected before sending, e.g. too large; shown in the queue like a failed upload
  const reject = useCallback(
    (file: File, error: string) => {
      append([{ file, status: UploadStatus.FAILED, progress: 0, error }]);
    },
    [append]
  );

  const dismiss = useCallback((key: string) => {
    setUploads((prev) => prev.filter((item) => item.key !== key));
  }, []);

  return { uploads, add, reject, dismiss };
}

export function useUpdateImageNotes(gridId: number | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ imageId, notes }: { imageId: string; notes: string }) => updateImageNotes(imageId, notes),
    onSuccess: (updated) => {
      queryClient.setQueryData<ImageAsset[]>(gridImagesKey(gridId), (prev) =>
        prev?.map((image) => (image.id === updated.id ? updated : image))
      );
    },
  });
}

export function useDeleteGridImage(gridId: number | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (imageId: string) => deleteGridImage(gridId as number, imageId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: gridImagesKey(gridId) }),
  });
}

/**
 * Saves a new image order. The cached list reorders at once so the dropped thumb stays put;
 * on failure, e.g. 409 after an upload landed mid-drag, it rolls back and refetches.
 */
export function useReorderGridImages(gridId: number | null) {
  const queryClient = useQueryClient();
  const key = gridImagesKey(gridId);

  return useMutation({
    mutationFn: (imageIds: string[]) => reorderGridImages(gridId as number, imageIds),
    onMutate: async (imageIds) => {
      await queryClient.cancelQueries({ queryKey: key });
      const previous = queryClient.getQueryData<ImageAsset[]>(key);

      const byId = new Map(previous?.map((image) => [image.id, image]));
      const reordered = imageIds.map((id) => byId.get(id)).filter((image) => image !== undefined);
      queryClient.setQueryData<ImageAsset[]>(key, reordered);

      return { previous };
    },
    onError: (_error, _imageIds, context) => queryClient.setQueryData(key, context?.previous),
    onSettled: () => queryClient.invalidateQueries({ queryKey: key }),
  });
}
