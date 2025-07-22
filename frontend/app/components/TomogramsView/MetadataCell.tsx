import React from 'react';
import { CellContext } from '@tanstack/react-table';
import { EntityDataTypes } from '@app/common/types/tableState';
import { useFetchData } from '../../../hooks/useFetchData/useFetchData';

export type MetadataCellValue = {
  sessionName: string;
  runNumber: string;
};

export const MetadataCell = (props: CellContext<EntityDataTypes, MetadataCellValue>) => {
  const { sessionName, runNumber } = props.getValue();
  const shouldFetch = sessionName && runNumber;
  const apiUrl = shouldFetch
    ? `http://umbrella.czbiohub.org/workflow/get_aretomo3?session=${encodeURIComponent(sessionName)}&run_id=${encodeURIComponent(runNumber)}`
    : '';

  const { data, isSuccess } = useFetchData<any>(apiUrl, {});

  if (!shouldFetch) return <span />;
  if (!isSuccess) return <span>Loading...</span>;
  if (!data) return <span>No data</span>;

  // Display the result (customize as needed)
  return <span>{typeof data === 'string' ? data : JSON.stringify(data)}</span>;
}; 