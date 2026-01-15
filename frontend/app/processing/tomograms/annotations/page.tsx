import { Metadata } from 'next';
import { AnnotationsView } from '@app/components/AnnotationsView/AnnotationsView';

export const metadata: Metadata = {
  title: 'Embrella Annotations',
};

const AnnotationsPage = () => {
  return <AnnotationsView />;
};

export default AnnotationsPage;
