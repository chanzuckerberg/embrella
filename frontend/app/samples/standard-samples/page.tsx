import { Metadata } from 'next';
import { StandardSamplesView } from '@app/components/StandardSamples/StandardSamplesView';

export const metadata: Metadata = {
  title: 'Standard Samples',
};

const StandardSamplesPage = () => {
  return <StandardSamplesView />;
};

export default StandardSamplesPage;
