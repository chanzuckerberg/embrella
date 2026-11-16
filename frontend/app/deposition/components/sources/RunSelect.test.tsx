import '@testing-library/jest-dom';
import { fireEvent, render, screen } from '@testing-library/react';

import { RunSelect } from './RunSelect';

afterEach(() => jest.restoreAllMocks());

it.each([false, true])('preserves a saved run while options load (allowNone=%s)', (allowNone) => {
  const warn = jest.spyOn(console, 'warn');
  const onChange = jest.fn();
  const props = {
    label: 'Run',
    placeholder: 'Select run',
    value: 'run001',
    options: [] as string[],
    loading: true,
    disabled: false,
    allowNone,
    onChange,
  };
  const { rerender } = render(<RunSelect {...props} />);
  expect(screen.getByRole('combobox')).toHaveTextContent('run001');
  expect(warn).not.toHaveBeenCalled();
  expect(onChange).not.toHaveBeenCalled();

  rerender(<RunSelect {...props} loading={false} options={['run001', 'run002']} />);
  fireEvent.mouseDown(screen.getByRole('combobox'));
  expect(screen.getAllByRole('option', { name: 'run001' })).toHaveLength(1);
  fireEvent.click(screen.getByRole('option', { name: 'run002' }));
  expect(onChange).toHaveBeenCalledWith('run002');
  expect(warn).not.toHaveBeenCalled();
});

it('preserves a saved run absent from the loaded list and still allows None', () => {
  const warn = jest.spyOn(console, 'warn');
  const onChange = jest.fn();
  render(
    <RunSelect
      label="DenoisET run"
      placeholder="Select run"
      value="run001"
      options={['run002']}
      loading={false}
      disabled={false}
      allowNone
      onChange={onChange}
    />
  );
  expect(screen.getByRole('combobox')).toHaveTextContent('run001');
  fireEvent.mouseDown(screen.getByRole('combobox'));
  fireEvent.click(screen.getByRole('option', { name: 'None' }));
  expect(onChange).toHaveBeenCalledWith('');
  expect(warn).not.toHaveBeenCalled();
});
