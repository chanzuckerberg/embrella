import { Metadata } from 'next';
import { redirect } from 'next/navigation';

export const metadata: Metadata = {
  title: 'Annotations',
};

export default function DataAnnotationsPage() {
  redirect('/annotations');
}
