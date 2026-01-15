import { Metadata } from 'next';
import { redirect } from 'next/navigation';

export const metadata: Metadata = {
  title: 'Cryo Grids',
};

export default function SamplesGridsPage() {
  redirect('/samples/cryo_grids');
}
