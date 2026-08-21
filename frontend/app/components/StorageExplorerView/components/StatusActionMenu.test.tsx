import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { StatusActionMenu } from './StatusActionMenu';
import { DecisionTarget } from '../types';

const SESSION_TARGET: DecisionTarget = {
  label: 'session 26mar02a',
  pathPrefixes: ['/base/aretomo3/26mar02a', '/base/denoise/26mar02a'],
  status: 'unset',
  totalSizeDisplay: '47.70 TB',
  directoryCount: 8714,
};

const INHERITED_RUN: DecisionTarget = {
  label: 'run run005',
  pathPrefixes: ['/base/aretomo3/26mar02a/run005'],
  status: 'delete',
  totalSizeDisplay: '15.08 TB',
  directoryCount: 2106,
  inheritedFrom: '/base/aretomo3/26mar02a',
};

function setup(target: DecisionTarget, onChoose = jest.fn().mockResolvedValue(undefined)) {
  const anchor = document.createElement('button');
  document.body.appendChild(anchor);
  const onClose = jest.fn();
  render(<StatusActionMenu anchor={anchor} target={target} onClose={onClose} onChoose={onChoose} />);
  return { onChoose, onClose };
}

describe('StatusActionMenu', () => {
  it('offers the same four options as the All Paths menu, and no "mixed"', () => {
    setup(SESSION_TARGET);

    expect(screen.getAllByRole('menuitem').map((item) => item.textContent)).toEqual([
      'Preserve',
      'Delete',
      'Review',
      'Unset',
    ]);
  });

  it('marks the current status as selected', () => {
    setup(INHERITED_RUN);

    expect(screen.getByRole('menuitem', { name: 'Delete' })).toHaveClass('Mui-selected');
    expect(screen.getByRole('menuitem', { name: 'Preserve' })).not.toHaveClass('Mui-selected');
  });

  it('records delete in one click, with no confirmation step', async () => {
    const { onChoose, onClose } = setup(SESSION_TARGET);

    await userEvent.click(screen.getByRole('menuitem', { name: 'Delete' }));

    // Nothing is destroyed and Unset reverses it, so a confirm would guard nothing.
    await waitFor(() => expect(onChoose).toHaveBeenCalledWith('delete', ''));
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('records the other statuses too', async () => {
    const { onChoose } = setup(SESSION_TARGET);

    await userEvent.click(screen.getByRole('menuitem', { name: 'Review' }));

    await waitFor(() => expect(onChoose).toHaveBeenCalledWith('review', ''));
  });

  it('clearing sends unset, which the backend turns into a row delete', async () => {
    const { onChoose } = setup(INHERITED_RUN);

    await userEvent.click(screen.getByRole('menuitem', { name: 'Unset' }));

    await waitFor(() => expect(onChoose).toHaveBeenCalledWith('unset', ''));
  });

  it('re-picking the current status writes nothing', async () => {
    const { onChoose, onClose } = setup(INHERITED_RUN);

    await userEvent.click(screen.getByRole('menuitem', { name: 'Delete' }));

    expect(onChoose).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it('says an inherited status came from above, without restating the path', () => {
    setup(INHERITED_RUN);

    expect(screen.getByText('Inherited from the tier above')).toBeInTheDocument();
    // The path is on the tag's tooltip; here it only crowded out the options.
    expect(screen.queryByText(/\/base\/aretomo3/)).not.toBeInTheDocument();
  });

  it('says nothing about inheritance when the decision is the row/s own', () => {
    setup({ ...INHERITED_RUN, inheritedFrom: null });

    expect(screen.queryByText(/Inherited from/)).not.toBeInTheDocument();
  });

  it('stays open and shows why when a write is rejected', async () => {
    const onChoose = jest.fn().mockRejectedValue(new Error('matches no directory'));
    const { onClose } = setup(SESSION_TARGET, onChoose);

    await userEvent.click(screen.getByRole('menuitem', { name: 'Delete' }));

    expect(await screen.findByText(/matches no directory/)).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });
});
