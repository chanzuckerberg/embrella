import { Metadata } from 'next';
import { redirect } from 'next/navigation';

export const metadata: Metadata = {
  title: 'Tomograms',
};

export default function DataTomogramsPage() {
  redirect('/tomograms');
}
