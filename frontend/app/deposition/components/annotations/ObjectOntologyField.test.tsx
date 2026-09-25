import '@testing-library/jest-dom';
import { type ComponentProps, useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { ObjectOntologyField } from './ObjectOntologyField';
import { searchOntology, validateOntologyId } from '../../services/ols';

jest.mock('../../services/ols', () => ({
  searchOntology: jest.fn(),
  validateOntologyId: jest.fn(),
  GO_CELLULAR_COMPONENT_IRI: 'http://purl.obolibrary.org/obo/GO_0005575',
}));

const mockSearch = searchOntology as jest.Mock;
const mockValidate = validateOntologyId as jest.Mock;

beforeEach(() => {
  mockSearch.mockResolvedValue([]);
  mockValidate.mockResolvedValue(null);
});
afterEach(() => jest.clearAllMocks());

function renderField(props: Partial<ComponentProps<typeof ObjectOntologyField>> = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const onChange = jest.fn();
  render(
    <QueryClientProvider client={client}>
      <ObjectOntologyField name="" id="" onChange={onChange} {...props} />
    </QueryClientProvider>
  );
  return { onChange };
}

it('backfills an empty object name from a resolvable ID', async () => {
  mockValidate.mockResolvedValue({ id: 'GO:0005886', label: 'plasma membrane', synonyms: [] });
  const { onChange } = renderField({ id: 'GO:0005886' });
  await waitFor(() => expect(onChange).toHaveBeenCalledWith({ object_name: 'plasma membrane' }));
});

it('does not overwrite an existing object name (e.g. imported from copick)', async () => {
  mockValidate.mockResolvedValue({ id: 'GO:0005886', label: 'plasma membrane', synonyms: [] });
  const { onChange } = renderField({ id: 'GO:0005886', name: 'membrane (copick)' });
  await screen.findByText(/plasma membrane/i); // the resolved label shows in the helper text
  expect(onChange).not.toHaveBeenCalled();
});

it('does not write into a disabled field', async () => {
  mockValidate.mockResolvedValue({ id: 'GO:0005886', label: 'plasma membrane', synonyms: [] });
  const { onChange } = renderField({ id: 'GO:0005886', disabled: true });
  await screen.findByText(/plasma membrane/i);
  expect(onChange).not.toHaveBeenCalled();
});

it('clearing the object name also clears the ID and does not snap the name back', async () => {
  mockValidate.mockResolvedValue({ id: 'GO:0005886', label: 'plasma membrane', synonyms: [] });
  const onChangeSpy = jest.fn();
  function Controlled() {
    const [pair, setPair] = useState({ object_name: '', object_id: 'GO:0005886' });
    return (
      <ObjectOntologyField
        name={pair.object_name}
        id={pair.object_id}
        onChange={(patch) => {
          onChangeSpy(patch);
          setPair((previous) => ({
            object_name: patch.object_name ?? previous.object_name,
            object_id: patch.object_id ?? previous.object_id,
          }));
        }}
      />
    );
  }
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <Controlled />
    </QueryClientProvider>
  );
  // The resolvable ID backfills the empty name first.
  await waitFor(() => expect(screen.getByLabelText(/object name/i)).toHaveValue('plasma membrane'));
  await userEvent.clear(screen.getByLabelText(/object name/i));
  // Clearing the name drops the ID too, so the effect can't restore the label.
  expect(onChangeSpy).toHaveBeenCalledWith({ object_name: '', object_id: '' });
  await waitFor(() => expect(screen.getByLabelText(/object name/i)).toHaveValue(''));
  expect(screen.getByLabelText(/object id/i)).toHaveValue('');
});
