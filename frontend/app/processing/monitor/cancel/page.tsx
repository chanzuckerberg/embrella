'use client';

import { useEffect } from 'react';
import { DJANGO_URL } from '@app/common/constants/api';

export default function CancelJobsPage() {
  useEffect(() => {
    window.location.href = `${DJANGO_URL}/workflow/cancel`;
  }, []);

  return null;
}
