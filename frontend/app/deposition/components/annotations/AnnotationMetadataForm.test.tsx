import '@testing-library/jest-dom';
import { fireEvent, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { AnnotationMetadataForm } from './AnnotationMetadataForm';
import type { DepositionAnnotation } from '../../types';

const base: DepositionAnnotation = { copick_kind: 'picks', copick_ref: 'ribosome:relion/1' };

function setup(over: Partial<DepositionAnnotation> = {}, readOnly = false) {
  const onChange = jest.fn();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <AnnotationMetadataForm annotation={{ ...base, ...over }} onChange={onChange} readOnly={readOnly} />
    </QueryClientProvider>
  );
  return { onChange };
}

it('renders the value of a text field', () => {
  setup({ object_name: 'ribosome' });
  expect(screen.getByLabelText('Object name')).toHaveValue('ribosome');
});

it('emits a patch when a text field changes', () => {
  const { onChange } = setup();
  fireEvent.change(screen.getByLabelText('Object name'), { target: { value: 'ribosome' } });
  expect(onChange).toHaveBeenCalledWith({ object_name: 'ribosome' });
});

it('parses object count as a number and clears empty to null', () => {
  const { onChange } = setup({ object_count: 5 });
  fireEvent.change(screen.getByLabelText('Object count'), { target: { value: '1200' } });
  expect(onChange).toHaveBeenCalledWith({ object_count: 1200 });
  fireEvent.change(screen.getByLabelText('Object count'), { target: { value: '' } });
  expect(onChange).toHaveBeenCalledWith({ object_count: null });
});

it('toggles a boolean flag', () => {
  const { onChange } = setup();
  fireEvent.click(screen.getByLabelText('Ground truth'));
  expect(onChange).toHaveBeenCalledWith({ ground_truth_status: true });
});

it('disables all inputs when readOnly', () => {
  setup({ object_name: 'x' }, true);
  expect(screen.getByLabelText('Object name')).toBeDisabled();
  expect(screen.getByLabelText('Ground truth')).toBeDisabled();
});

it('adds a method link with a default type', () => {
  const { onChange } = setup();
  fireEvent.click(screen.getByRole('button', { name: /add link/i }));
  expect(onChange).toHaveBeenCalledWith({ method_links: [{ link_type: 'source_code', link: '' }] });
});

it('edits an existing method link url', () => {
  const { onChange } = setup({ method_links: [{ id: 1, link_type: 'website', link: '' }] });
  fireEvent.change(screen.getByLabelText(/Link URL/), { target: { value: 'https://example.org' } });
  expect(onChange).toHaveBeenCalledWith({
    method_links: [{ id: 1, link_type: 'website', link: 'https://example.org' }],
  });
});
