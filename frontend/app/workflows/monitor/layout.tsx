import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Workflow Monitor',
};

export default function WorkflowMonitorLayout({ children }: { children: React.ReactNode }) {
  return children;
}
