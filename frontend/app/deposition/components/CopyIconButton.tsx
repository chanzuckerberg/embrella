'use client';

import { useEffect, useRef, useState } from 'react';
import { Icon } from '@czi-sds/components';
import { IconButton } from '@mui/material';

type CopyState = 'idle' | 'ok' | 'fail';

const VARIANTS = {
  idle: { icon: 'Copy', tone: 'gray', shade: 500, title: 'Copy', aria: 'Copy' },
  ok: { icon: 'Check', tone: 'green', shade: 400, title: 'Copied!', aria: 'Copied' },
  fail: { icon: 'ExclamationMarkCircle', tone: 'red', shade: 400, title: 'Unable to copy', aria: "Couldn't copy" },
} as const;

// Small copy-to-clipboard affordance for read-only values; briefly shows success or failure.
export function CopyIconButton({ value, label }: { value: string; label: string }) {
  const [state, setState] = useState<CopyState>('idle');
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => clearTimeout(timer.current ?? undefined), []);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setState('ok');
    } catch {
      setState('fail'); // value stays selectable to copy manually
    }
    clearTimeout(timer.current ?? undefined);
    timer.current = setTimeout(() => setState('idle'), 1500);
  };

  const v = VARIANTS[state];
  return (
    <IconButton size="small" onClick={copy} aria-label={`${v.aria} ${label}`} title={v.title}>
      <Icon sdsIcon={v.icon} sdsSize="xs" color={v.tone} shade={v.shade} />
    </IconButton>
  );
}
