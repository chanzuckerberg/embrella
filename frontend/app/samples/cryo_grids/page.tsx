import { Metadata } from 'next';
import { GridInventory } from '@app/components/GridInventory/GridInventory';

export const metadata: Metadata = {
  title: 'Embrella Grids',
};

const GridsPage = () => {
  return <GridInventory />;
};

export default GridsPage;
