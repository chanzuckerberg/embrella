import { Metadata } from 'next';
import { ScreeningView } from '@app/components/Screening/ScreeningView';

export const metadata: Metadata = {
  title: 'Screening',
};

const ScreeningPage = () => {
  return <ScreeningView />;
};

export default ScreeningPage;
