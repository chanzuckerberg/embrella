import '@testing-library/jest-dom';
import { fireEvent, render, screen } from '@testing-library/react';

import { FreeTextOptionField } from './FreeTextOptionField';

const OPTIONS = [
  { value: 'b.gain', label: 'b.gain (most recent)' },
  { value: 'a.gain', label: 'a.gain' },
];

function renderField(value = '', options = OPTIONS) {
  const onChange = jest.fn();
  render(
    <FreeTextOptionField name="gain_file_name" label="Gain" value={value} options={options} onChange={onChange} />
  );
  return onChange;
}

describe('FreeTextOptionField', () => {
  it('shows the selected option by its label', () => {
    renderField('b.gain');
    expect(screen.getByRole('combobox')).toHaveValue('b.gain (most recent)');
  });

  it('reports typed text as the value', () => {
    const onChange = renderField();
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '/abs/ref.gain' } });
    expect(onChange).toHaveBeenLastCalledWith('gain_file_name', '/abs/ref.gain');
  });

  it('reports a picked option by its value, not its label', () => {
    const onChange = renderField();
    const input = screen.getByRole('combobox');
    fireEvent.mouseDown(input);
    fireEvent.click(screen.getByText('a.gain'));
    expect(onChange).toHaveBeenLastCalledWith('gain_file_name', 'a.gain');
  });

  it('locks the input while a listed option is shown', () => {
    renderField('b.gain');
    expect(screen.getByRole('combobox')).toHaveAttribute('readonly');
  });

  it('clearing a listed option empties the value and unlocks typing', () => {
    const onChange = renderField('b.gain');
    fireEvent.click(screen.getByTitle('Clear'));
    expect(onChange).toHaveBeenLastCalledWith('gain_file_name', '');
  });

  it('a typed path is editable', () => {
    renderField('/abs/ref.gain');
    expect(screen.getByRole('combobox')).not.toHaveAttribute('readonly');
  });

  it('stays editable with no options', () => {
    renderField('', []);
    expect(screen.getByRole('combobox')).toBeEnabled();
  });
});
