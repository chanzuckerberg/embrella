import React, { useState,Fragment, useEffect } from 'react';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import {
  ButtonDropdown,
  CellComponent,
  CellHeader,
  Table,
  TableHeader,
  TableRow,
  Alert
} from "@czi-sds/components";
import { TableBody } from '@mui/material';
import { TableStateProvider } from "@app/common/components/TableStateProvider/TableStateProvider";
import { EntityTable } from "@app/common/components/EntityTable/EntityTable";
import { SortingState, flexRender } from "@tanstack/react-table";
import { METADATA_COLUMN_DEFS } from "./constants/columns";
import { MetadataSummaryResponse } from "@app/common/types/metadataViz/metadataSummary"; 
import { TableWrapper } from '@app/common/components/TableWrapper/TableWrapper';
import { useFetchMetadataSummary } from "@app/common/hooks/useFetchMetadata/useFetchMetadataSummary";
import { Card, CardContent, CardHeader, Divider } from '@mui/material';
import { API } from "@app/common/constants/api";
import { FilterableTableMain } from "@app/common/components/FilterableTableMain/FilterableTableMain";

interface MetadataSummaryProps {
  sessionName: string;
  runNumber: string;
}

export const MetadataSummary: React.FC<MetadataSummaryProps> = ({ sessionName, runNumber }) => {
  const [showSummary, setShowSummary] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [shouldFetchData, setShouldFetchData] = useState(false);
  const { data, isSuccess, error } = useFetchMetadataSummary(sessionName, runNumber, shouldFetchData);

  useEffect(() => {
    if (error) {
      console.log('Error fetching metadata:', error);
    }
  }, [error]);

  const initialSortState: SortingState = [
    { desc: false, id: "name" },
  ];

  const handleToggleSummary = () => {
    if (!showSummary) {
      setIsLoading(true);
      setShouldFetchData(true);
    } else {
      setIsLoading(false);
    }
    setShowSummary(!showSummary);
  };

  if (isLoading && !isSuccess) {
    return <div className="p-4">Loading...</div>;
  }

  if (error) {
    const errorMessage = error.status === 404 
      ? 'Required files not found. Please check if the session and run number are correct.'
      : error.message || 'An error occurred while fetching metadata';

    return (
      <div className="w-full">
        <Alert severity="warning">
          {errorMessage}
        </Alert>
      </div>
    );
  }
  return (
    <div className="w-full">
      <ButtonDropdown 
        sdsType="primary" 
        sdsStyle="rounded" 
        onClick={handleToggleSummary}
        style={{ margin: '10px' }}
        disabled={isLoading && !isSuccess}
      >
        {showSummary ? 'Hide Summary' : 'Show Summary'}
      </ButtonDropdown>

      {showSummary && data && (
        <Paper sx={{ p: 3, bgcolor: 'background.paper', borderRadius: 1, mt: 1 }}>
          <Card elevation={2} sx={{ mb: 3 }}>
            <CardHeader 
              title="Session Summary" 
              sx={{ 
                bgcolor: 'primary.dark',
                color: 'primary.contrastText',
                '& .MuiCardHeader-title': {
                  fontSize: '1.25rem',
                  fontWeight: 500
                }
              }} 
            />
            <CardContent>
              <Typography variant="body1" sx={{ mb: 1 }}>
                <strong>Session:</strong> {data.session_name}
              </Typography>
              <Typography variant="body1" sx={{ mb: 1 }}>
                <strong>Run:</strong> {data.run_number}
              </Typography>
              <Divider sx={{ my: 2 }} />
              <Typography variant="body1" sx={{ mb: 1, wordBreak: 'break-all' }}>
                <strong>Data Collection Path:</strong> {data.data_collection_directory}
              </Typography>
              <Typography variant="body1" sx={{ wordBreak: 'break-all' }}>
                <strong>Aretomo3 Processing Path:</strong> {data.aretomo3_processing_directory}
              </Typography>
            </CardContent>
          </Card>

          {data.computed_metrics && data.computed_metrics.length > 0 ? (
            <div className="mt-4">
               <TableStateProvider initialSortState={initialSortState}>
                <Fragment>
                  <FilterableTableMain>
                    <TableWrapper>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            {METADATA_COLUMN_DEFS.map((col) => (
                              <CellHeader 
                                key={col.id}
                                active={false}
                                direction={col.enableSorting ? "asc" : undefined}
                                hideSortIcon={!col.enableSorting}
                                onClick={col.enableSorting ? () => {} : undefined}
                              >
                                {flexRender(col.header, {})}
                              </CellHeader>
                            ))}
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {data.computed_metrics.map((row, i) => (
                            <TableRow key={i}>
                              {METADATA_COLUMN_DEFS.map((col) => (
                                <CellComponent key={col.id}>
                                  {col.cell ? 
                                    col.cell({ getValue: () => row[col.accessorKey as keyof typeof row] }) :
                                    row[col.accessorKey as keyof typeof row]
                                  }
                                </CellComponent>
                              ))}
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableWrapper>
                  </FilterableTableMain>
                </Fragment>
              </TableStateProvider>
            </div>
          ) : (
            <Typography variant="body1" className="mt-4">No metrics data available</Typography>
          )}
        </Paper>
      )}
    </div>
  );
};