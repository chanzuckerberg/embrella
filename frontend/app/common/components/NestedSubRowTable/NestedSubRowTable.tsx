import React, { useState } from 'react';
import { Box, Collapse, IconButton, Table, TableBody, TableCell, TableHead, TableRow } from '@mui/material';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';
import {
  ColumnDef,
  Row,
  flexRender,
  getCoreRowModel,
  getExpandedRowModel,
  useReactTable,
  type ExpandedState,
} from '@tanstack/react-table';

import { StyledHeaderCell, StyledTableCell } from '@app/common/components/EntityTable/EntityTable';

interface NestedSubRowTableProps<T> {
  /** Rows for this tier. Already ordered — this component never sorts. */
  data: T[];
  columnDefs: ColumnDef<T>[];
  /** Stable, namespaced row id. Ids are not scoped by depth (see EntityTable's getRowId). */
  getRowId: (row: T) => string;
  /**
   * Children of a row. Returning an empty array makes the row non-expandable,
   * which is what drives whether a chevron is drawn at all.
   */
  getChildren?: (row: T) => unknown[];
  /** Rendered inside the expanded region. Only called for expandable rows. */
  renderChild?: (row: T) => React.ReactNode;
  /** Shown instead of the table when `data` is empty. */
  emptyMessage: string;
  minWidth?: number;
  /** Accessible names for the toggle, e.g. 'runs' -> "Expand runs". */
  childLabel?: string;
}

/**
 * One tier of an expandable sub-row table, for use inside EntityTable's
 * `renderSubRow`.
 *
 * EntityTable skips rows at depth > 0 in its own render loop, so nested tiers
 * have to be rendered by the consumer rather than by TanStack's flattened row
 * model. This component is that renderer: a self-contained table instance with
 * its own local expansion state, reusing EntityTable's cell styling so the
 * tiers line up visually.
 *
 * `Collapse unmountOnExit` matters beyond animation: a child that fetches on
 * mount will not fire until first expand, and will not fire at all for a row
 * the user never opens. Do not remove it without checking consumers that rely
 * on that for lazy loading.
 */
export const NestedSubRowTable = <T,>({
  data,
  columnDefs,
  getRowId,
  getChildren,
  renderChild,
  emptyMessage,
  minWidth = 520,
  childLabel = 'details',
}: NestedSubRowTableProps<T>): React.JSX.Element => {
  const [expanded, setExpanded] = useState<ExpandedState>({});

  const table = useReactTable<T>({
    data,
    columns: columnDefs,
    state: { expanded },
    onExpandedChange: setExpanded,
    getCoreRowModel: getCoreRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    getRowId,
    // Not getSubRows: children are rendered by renderChild, not by TanStack's
    // row model, so this only needs to answer "is there anything to open".
    getRowCanExpand: (row: Row<T>) => Boolean(getChildren?.(row.original)?.length),
  });

  if (data.length === 0) {
    return <span style={{ color: '#999', fontStyle: 'italic' }}>{emptyMessage}</span>;
  }

  const headers = table.getFlatHeaders();
  const isExpandable = Boolean(getChildren && renderChild);

  return (
    <Table size="small" sx={{ tableLayout: 'fixed', minWidth }}>
      <TableHead>
        <TableRow>
          {!!isExpandable && <StyledHeaderCell width={40} />}
          {headers.map((header) => (
            <StyledHeaderCell key={header.id} width={header.column.columnDef.size}>
              {flexRender(header.column.columnDef.header, header.getContext())}
            </StyledHeaderCell>
          ))}
        </TableRow>
      </TableHead>
      <TableBody>
        {table.getRowModel().rows.map((row) => {
          const canExpand = isExpandable && row.getCanExpand();
          const isExpanded = row.getIsExpanded();

          return (
            <React.Fragment key={row.id}>
              <TableRow
                hover
                sx={{
                  ...(canExpand ? { cursor: 'pointer' } : {}),
                  '&:last-child td': { borderBottom: 0 },
                }}
                onClick={canExpand ? () => row.toggleExpanded() : undefined}
              >
                {!!isExpandable && (
                  <StyledTableCell width={40} sx={{ px: 0.5 }}>
                    {!!canExpand && (
                      <IconButton
                        size="small"
                        aria-label={isExpanded ? `Collapse ${childLabel}` : `Expand ${childLabel}`}
                        onClick={(e) => {
                          // The row itself toggles too; without this the row
                          // handler fires second and immediately undoes it.
                          e.stopPropagation();
                          row.toggleExpanded();
                        }}
                      >
                        {isExpanded ? (
                          <KeyboardArrowDownIcon fontSize="small" />
                        ) : (
                          <KeyboardArrowRightIcon fontSize="small" />
                        )}
                      </IconButton>
                    )}
                  </StyledTableCell>
                )}
                {row.getVisibleCells().map((cell) => (
                  <StyledTableCell key={cell.id} width={cell.column.columnDef.size}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </StyledTableCell>
                ))}
              </TableRow>

              {!!canExpand && (
                <TableRow sx={!isExpanded ? { display: 'none' } : undefined}>
                  <TableCell colSpan={headers.length + 1} sx={{ p: 0 }}>
                    <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                      <Box sx={{ pl: 4, pr: 2, py: 1, bgcolor: '#f0f0f0', minWidth: 'fit-content' }}>
                        {renderChild?.(row.original)}
                      </Box>
                    </Collapse>
                  </TableCell>
                </TableRow>
              )}
            </React.Fragment>
          );
        })}
      </TableBody>
    </Table>
  );
};
