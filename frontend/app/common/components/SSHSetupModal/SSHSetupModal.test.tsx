import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { SSHSetupModal } from './SSHSetupModal';
import { postResource } from '@app/common/queries/fetchResource';

jest.mock('@app/common/queries/fetchResource', () => ({ postResource: jest.fn() }));

it('sets up SSH for a configured institutional cluster', async () => {
  (postResource as jest.Mock).mockResolvedValue({
    json: async () => ({ success: true, can_connect: true }),
  });
  const onSuccess = jest.fn();
  render(
    <SSHSetupModal open cluster="stanford-hpc" defaultUsername="alice" onClose={jest.fn()} onSuccess={onSuccess} />
  );
  expect(screen.getByLabelText('Username')).toHaveValue('alice');
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'test-password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Setup SSH' }));
  await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1));
  expect(postResource).toHaveBeenCalledWith(
    expect.any(String),
    expect.objectContaining({ cluster_id: 'stanford-hpc', username: 'alice' })
  );
});
