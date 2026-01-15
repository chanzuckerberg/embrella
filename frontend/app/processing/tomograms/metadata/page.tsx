import { Metadata } from 'next';
import { TomogramsView } from '@app/components/TomogramsView/TomogramsView';

export const metadata: Metadata = {
  title: 'Embrella Tomograms',
};

const TomogramsPage = () => {
  return <TomogramsView />;
};

export default TomogramsPage;
