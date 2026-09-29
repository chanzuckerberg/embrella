import '@testing-library/jest-dom';
import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { BiologicalClassification } from './BiologicalClassification';
import { searchOntology, validateOntologyId } from '../../../services/ols';
import type { DatasetSample } from '../../../types';

jest.mock('../../../services/ols', () => ({
  ...jest.requireActual('../../../services/ols'),
  searchOntology: jest.fn(),
  validateOntologyId: jest.fn(),
}));

const mockSearch = searchOntology as jest.Mock;
const mockValidate = validateOntologyId as jest.Mock;

beforeEach(() => {
  mockSearch.mockResolvedValue([]);
  mockValidate.mockResolvedValue(null);
});
afterEach(() => jest.clearAllMocks());

function renderBio() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function Controlled() {
    const [sample, setSample] = useState<DatasetSample>({});
    return (
      <BiologicalClassification
        sample={sample}
        requiredBioField={null}
        assayLabel=""
        assayOntologyId=""
        onChangeSample={(key, value) => setSample((previous) => ({ ...previous, [key]: value }))}
        onChangeAssayLabel={jest.fn()}
        onChangeAssayOntologyId={jest.fn()}
        readOnly={false}
        innerRef={() => {}}
      />
    );
  }
  render(
    <QueryClientProvider client={client}>
      <Controlled />
    </QueryClientProvider>
  );
}

it('scopes the Cell component GO search to the cellular component branch', async () => {
  renderBio();
  await userEvent.click(screen.getByRole('button', { name: /Cell component/i }));
  await userEvent.type(screen.getByLabelText(/Cell component name/i), 'mitochondrion');
  await waitFor(() =>
    expect(mockSearch).toHaveBeenCalledWith('mitochondrion', 'go', 'http://purl.obolibrary.org/obo/GO_0005575')
  );
});
