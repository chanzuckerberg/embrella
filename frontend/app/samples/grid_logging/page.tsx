import { Metadata } from 'next';
import { GridsLogging } from '@app/components/GridsLogging/GridsLogging';

export const metadata: Metadata = {
  title: 'Embrella Grids Logging',
};

const GridsPage = () => {
  return <GridsLogging />;
};

export default GridsPage;
