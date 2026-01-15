import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Job Logs',
};

export default function LogsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
