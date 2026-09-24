import '@testing-library/jest-dom';
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
  render(
    <QueryClientProvider client={client}>
      <BiologicalClassification
        sample={{} as DatasetSample}
        requiredBioField={null}
        assayLabel=""
        assayOntologyId=""
        onChangeSample={jest.fn()}
        onChangeAssayLabel={jest.fn()}
        onChangeAssayOntologyId={jest.fn()}
        readOnly={false}
        innerRef={() => {}}
      />
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
