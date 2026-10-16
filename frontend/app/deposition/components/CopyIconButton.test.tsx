import '@testing-library/jest-dom';
import { fireEvent, render, screen } from '@testing-library/react';
import { CopyIconButton } from './CopyIconButton';

const originalClipboard = Object.getOwnPropertyDescriptor(navigator, 'clipboard');
afterEach(() => {
  if (originalClipboard) Object.defineProperty(navigator, 'clipboard', originalClipboard);
  else Reflect.deleteProperty(navigator, 'clipboard');
});

it.each([true, false])('announces the copy result when clipboard success is %s', async (success) => {
  const writeText = jest.fn();
  if (success) writeText.mockResolvedValue(undefined);
  else writeText.mockRejectedValue(new Error('denied'));
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
  render(<CopyIconButton value="GO:0005886" label="ontology ID" />);
  fireEvent.click(screen.getByRole('button', { name: 'Copy ontology ID' }));
  expect(
    await screen.findByRole('button', {
      name: success ? 'Copied ontology ID' : "Couldn't copy ontology ID",
    })
  ).toBeInTheDocument();
  expect(writeText).toHaveBeenCalledWith('GO:0005886');
});
