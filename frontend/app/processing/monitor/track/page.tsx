'use client';

import { useEffect } from 'react';
import { DJANGO_URL } from '@app/common/constants/api';

export default function TrackJobsPage() {
  useEffect(() => {
    window.location.href = `${DJANGO_URL}/workflow/track`;
  }, []);

  return null;
}
