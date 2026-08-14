import { Metadata } from 'next';
import { StorageExplorerView } from '@app/components/StorageExplorerView';

export const metadata: Metadata = {
  title: 'Embrella Storage Explorer',
};

const StorageExplorerPage = () => {
  return <StorageExplorerView />;
};

export default StorageExplorerPage;
