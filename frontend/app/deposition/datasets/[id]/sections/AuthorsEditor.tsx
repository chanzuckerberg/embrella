'use client';

import type { AuthorRef } from '../../../types';
import { AuthorListEditor } from '../../../components/AuthorListEditor';

export function AuthorsEditor({
  authors,
  onChange,
  disabled = false,
}: {
  authors: AuthorRef[];
  onChange: (authors: AuthorRef[]) => void;
  disabled?: boolean;
}) {
  return <AuthorListEditor authors={authors} onChange={onChange} disabled={disabled} />;
}
