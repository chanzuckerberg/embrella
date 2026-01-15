import { Metadata } from 'next';
import { JobsManagementView } from './components/JobsManagementView';

export const metadata: Metadata = {
  title: 'Job Monitor',
};

export default function ProcessingMonitorPage() {
  return <JobsManagementView />;
}
