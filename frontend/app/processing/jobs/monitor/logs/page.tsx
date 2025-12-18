'use client';

import { useEffect } from 'react';
import { DJANGO_URL } from '@app/common/constants/api';

export default function JobLogsPage() {
  useEffect(() => {
    window.location.href = `${DJANGO_URL}/workflow/logs`;
  }, []);

  return null;
}
