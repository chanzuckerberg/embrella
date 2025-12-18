import { Metadata } from 'next';
import { DirectoryExplorerView } from '@app/components/DirectoryExplorerView';

export const metadata: Metadata = {
  title: 'Embrella Storage Explorer',
};

const StorageExplorerPage = () => {
  return <DirectoryExplorerView />;
};

export default StorageExplorerPage;
