import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ColumnDef } from '@tanstack/react-table';

import { NestedSubRowTable } from './NestedSubRowTable';

interface Child {
  id: string;
  label: string;
}

interface Group {
  id: string;
  name: string;
  children: Child[];
}

const COLUMNS: ColumnDef<Group>[] = [
  { id: 'name', accessorFn: (group) => group.name, header: 'Name', size: 100 },
  { id: 'count', accessorFn: (group) => `${group.children.length} items`, header: 'Count', size: 80 },
];

const GROUPS: Group[] = [
  { id: 'g-1', name: 'alpha', children: [{ id: 'c-1', label: 'alpha-child' }] },
  // Two children so its count cell differs from alpha's — otherwise a
  // getByText on the count is ambiguous.
  { id: 'g-2', name: 'beta', children: [{ id: 'c-2', label: 'beta-child' }, { id: 'c-3', label: 'beta-child-2' }] },
  { id: 'g-3', name: 'gamma', children: [] },
];

/** Child that reports when it actually mounts, so lazy loading can be asserted. */
const ChildProbe = ({ group, onMount }: { group: Group; onMount?: () => void }) => {
  React.useEffect(() => {
    onMount?.();
  }, [onMount]);
  return <div data-testid={`child-${group.id}`}>{group.children.map((child) => child.label).join(', ')}</div>;
};

const renderTable = (props: Partial<React.ComponentProps<typeof NestedSubRowTable<Group>>> = {}) =>
  render(
    <NestedSubRowTable<Group>
      data={GROUPS}
      columnDefs={COLUMNS}
      getRowId={(group) => group.id}
      getChildren={(group) => group.children}
      renderChild={(group) => <ChildProbe group={group} />}
      emptyMessage="Nothing here"
      childLabel="items"
      {...props}
    />
  );

describe('NestedSubRowTable', () => {
  it('renders one row per item', () => {
    renderTable();

    expect(screen.getByText('alpha')).toBeInTheDocument();
    expect(screen.getByText('beta')).toBeInTheDocument();
    expect(screen.getByText('1 items')).toBeInTheDocument();
  });

  it('keeps children unmounted until expanded', async () => {
    renderTable();

    expect(screen.queryByTestId('child-g-1')).not.toBeInTheDocument();

    await userEvent.click(screen.getAllByRole('button', { name: 'Expand items' })[0]);

    expect(screen.getByTestId('child-g-1')).toBeInTheDocument();
    // Siblings stay closed — expansion state is per row.
    expect(screen.queryByTestId('child-g-2')).not.toBeInTheDocument();
  });

  it('collapses again on a second click', async () => {
    renderTable();

    await userEvent.click(screen.getAllByRole('button', { name: 'Expand items' })[0]);
    expect(screen.getByTestId('child-g-1')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Collapse items' }));
    expect(screen.queryByTestId('child-g-1')).not.toBeInTheDocument();
  });

  it('expands when the row itself is clicked, not only the chevron', async () => {
    renderTable();

    await userEvent.click(screen.getByText('alpha'));

    expect(screen.getByTestId('child-g-1')).toBeInTheDocument();
  });

  it('offers no toggle for a row with no children', () => {
    renderTable();

    // alpha and beta have children; gamma does not.
    expect(screen.getAllByRole('button', { name: 'Expand items' })).toHaveLength(2);
  });

  it('does not mount children before first expand', async () => {
    // The guarantee is about *mounting*, not about renderChild being called:
    // the element is built eagerly, but Collapse's unmountOnExit keeps the
    // component out of the tree, so its effects never run. That is what makes
    // a sub-row that fetches on mount safe for a row nobody opens.
    const onMount = jest.fn();
    renderTable({ renderChild: (group) => <ChildProbe group={group} onMount={onMount} /> });

    expect(onMount).not.toHaveBeenCalled();

    await userEvent.click(screen.getAllByRole('button', { name: 'Expand items' })[0]);

    expect(onMount).toHaveBeenCalledTimes(1);
  });

  it('shows the empty message instead of a table when there are no rows', () => {
    renderTable({ data: [] });

    expect(screen.getByText('Nothing here')).toBeInTheDocument();
    expect(screen.queryByText('Name')).not.toBeInTheDocument();
  });

  it('renders a flat table with no chevron column when children are not configured', () => {
    renderTable({ getChildren: undefined, renderChild: undefined });

    expect(screen.getByText('alpha')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Expand items' })).not.toBeInTheDocument();
  });
});
