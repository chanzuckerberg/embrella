import { Metadata } from 'next';
import { HistoricalJobsView } from './components/HistoricalJobsView';

export const metadata: Metadata = {
  title: 'Job Logs',
};

export default function JobLogsPage() {
  return <HistoricalJobsView />;
}
