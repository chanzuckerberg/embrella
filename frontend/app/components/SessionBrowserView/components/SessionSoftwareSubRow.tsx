import React, { useMemo, useState } from 'react';
import { Box, Collapse, IconButton, Table, TableBody, TableCell, TableHead, TableRow } from '@mui/material';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';
import {
  flexRender,
  getCoreRowModel,
  getExpandedRowModel,
  useReactTable,
  type ExpandedState,
} from '@tanstack/react-table';

import { StyledHeaderCell, StyledTableCell } from '@app/common/components/EntityTable/EntityTable';

import { SESSION_SOFTWARE_COLUMN_DEFS } from '../constants/softwareColumns';
import { SessionOverviewData, SessionSoftwareGroup } from '../types';
import { groupRunsBySoftware } from '../utils/groupRunsBySoftware';
import { SoftwareRunsSubRow } from './SoftwareRunsSubRow';

interface SessionSoftwareSubRowProps {
  data: SessionOverviewData;
}

/**
 * Middle tier of the session browser: one row per processing-software display
 * name, each expanding to that software's runs.
 *
 * Note this shows every software on the session even when a
 * `processingSoftware` filter is active
 */
export const SessionSoftwareSubRow = ({ data }: SessionSoftwareSubRowProps) => {
  const [expanded, setExpanded] = useState<ExpandedState>({});
  const groups = useMemo(() => groupRunsBySoftware(data), [data]);

  const table = useReactTable<SessionSoftwareGroup>({
    data: groups,
    columns: SESSION_SOFTWARE_COLUMN_DEFS,
    state: { expanded },
    onExpandedChange: setExpanded,
    getCoreRowModel: getCoreRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    getRowId: (row) => row.id,
    getRowCanExpand: (row) => row.original.runs.length > 0,
  });

  if (groups.length === 0) {
    return <span style={{ color: '#999', fontStyle: 'italic' }}>No processing runs for this session</span>;
  }

  return (
    <Table size="small" sx={{ tableLayout: 'fixed', minWidth: 520 }}>
      <TableHead>
        <TableRow>
          <StyledHeaderCell width={40} />
          {table.getFlatHeaders().map((header) => (
            <StyledHeaderCell key={header.id} width={header.column.columnDef.size}>
              {flexRender(header.column.columnDef.header, header.getContext())}
            </StyledHeaderCell>
          ))}
        </TableRow>
      </TableHead>
      <TableBody>
        {table.getRowModel().rows.map((row) => {
          const canExpand = row.getCanExpand();
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
                <StyledTableCell width={40} sx={{ px: 0.5 }}>
                  {canExpand && (
                    <IconButton
                      size="small"
                      aria-label={isExpanded ? 'Collapse runs' : 'Expand runs'}
                      onClick={(e) => {
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
                {row.getVisibleCells().map((cell) => (
                  <StyledTableCell key={cell.id} width={cell.column.columnDef.size}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </StyledTableCell>
                ))}
              </TableRow>

              {canExpand && (
                <TableRow sx={!isExpanded ? { display: 'none' } : undefined}>
                  <TableCell colSpan={table.getFlatHeaders().length + 1} sx={{ p: 0 }}>
                    <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                      <Box sx={{ pl: 4, pr: 2, py: 1, bgcolor: '#f0f0f0', minWidth: 'fit-content' }}>
                        <SoftwareRunsSubRow runs={row.original.runs} />
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
