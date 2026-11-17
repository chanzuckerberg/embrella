import '@testing-library/jest-dom';
import { fireEvent, render, screen, within } from '@testing-library/react';

import WorkflowLaunchPage from './page';
import { fetchProcessorSchema, listProcessors } from '@app/common/services/workflowApi';

jest.mock('@app/common/services/workflowApi', () => ({
  listProcessors: jest.fn(),
  fetchProcessorSchema: jest.fn(),
}));
// The schema-driven form is exercised elsewhere; here it only shows which processor it got.
jest.mock('./components/WorkflowLaunchForm', () => ({
  __esModule: true,
  default: ({ processor }: { processor: { name: string } }) => <div>generic form for {processor.name}</div>,
}));
jest.mock('@app/common/components/SSHSetupModal', () => ({ SSHSetupModal: () => null }));

const CDPP = {
  name: 'cdpp',
  display_name: 'CryoET Data Portal Pipeline',
  version: '0.1.0',
  default_cluster: 'czii',
  allowed_clusters: [],
};

describe('WorkflowLaunchPage', () => {
  it('launches cdpp with the schema-driven form', async () => {
    (listProcessors as jest.Mock).mockResolvedValue([CDPP]);
    (fetchProcessorSchema as jest.Mock).mockResolvedValue({ processor: 'cdpp', schema: { properties: {} } });

    render(<WorkflowLaunchPage />);

    fireEvent.mouseDown(await screen.findByRole('combobox'));
    fireEvent.click(within(screen.getByRole('listbox')).getByText(/CryoET Data Portal Pipeline/));

    expect(await screen.findByText('generic form for cdpp')).toBeInTheDocument();
    expect(screen.queryByText(/does not have a dedicated form/)).not.toBeInTheDocument();
  });
});
