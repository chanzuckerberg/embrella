import React from 'react';
import Link from 'next/link';
import { Button, Icon } from '@czi-sds/components';
import { CellContext } from '@tanstack/react-table';
import { EntityDataTypes } from '@app/common/types/tableState';
import { TomogramData } from './types';

export const MetadataCell = (props: CellContext<EntityDataTypes, unknown>) => {
  const rowData = props.row.original as TomogramData | undefined;
  if (!rowData?.procPlan?.name?.includes('czii-live')) return <span />;

  const sessionName = rowData.msiSession?.name ?? '';
  const runNumber = (rowData.tomograms?.name ?? '').replace(/\s*\(id=\d+\)/g, '').trim();
  if (!sessionName || !runNumber) return <span />;

  const href = `/metadata/view/${encodeURIComponent(sessionName)}/${encodeURIComponent(runNumber)}`;
  return (
    <Link href={href} style={{ textDecoration: 'none' }}>
      <Button sdsType="secondary" sdsStyle="rounded" startIcon={<Icon sdsIcon="BarChartVertical3" sdsSize="s" />}>
        Summary
      </Button>
    </Link>
  );
};
