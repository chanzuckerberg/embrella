import { useEffect, useRef } from 'react';

export enum PasteMode {
  DOCUMENT = 'document', // Ctrl+V anywhere on the page uploads clipboard images
  OFF = 'off', // e.g. while another uploader on the page owns paste
}

const EDITABLE_TAGS = new Set(['INPUT', 'TEXTAREA', 'SELECT']);

/** Calls ``onFiles`` with clipboard images pasted on the page, except into text fields. */
export function usePasteImages(onFiles: (files: File[]) => void, mode: PasteMode) {
  // Latest callback without re-subscribing on every render
  const onFilesRef = useRef(onFiles);
  useEffect(() => {
    onFilesRef.current = onFiles;
  }, [onFiles]);

  useEffect(() => {
    if (mode === PasteMode.OFF) return;

    const handlePaste = (event: ClipboardEvent) => {
      // Pasting into Notes or another field keeps its normal behavior
      if (isEditable(event.target)) return;

      const images = Array.from(event.clipboardData?.files ?? []).filter((file) => file.type.startsWith('image/'));
      const files = withoutDuplicates(images);
      if (!files.length) return;

      event.preventDefault();
      onFilesRef.current(files);
    };

    document.addEventListener('paste', handlePaste);
    return () => document.removeEventListener('paste', handlePaste);
  }, [mode]);
}

/** Some sources put one image on the clipboard twice, e.g. "Copy Image" in a browser. */
function withoutDuplicates(files: File[]): File[] {
  const seen = new Set<string>();
  return files.filter((file) => {
    const id = `${file.type}:${file.size}`;
    if (seen.has(id)) return false;

    seen.add(id);
    return true;
  });
}

function isEditable(target: EventTarget | null): boolean {
  return target instanceof HTMLElement && (target.isContentEditable || EDITABLE_TAGS.has(target.tagName));
}
