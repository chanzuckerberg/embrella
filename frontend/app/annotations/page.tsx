import { Metadata } from 'next';
import { AnnotationsView } from '@app/components/AnnotationsView/AnnotationsView';

export const metadata: Metadata = {
  title: 'Embrella Annotations',
};

const AnntationsPage = () => {
  return <AnnotationsView />;
};

export default AnntationsPage;
