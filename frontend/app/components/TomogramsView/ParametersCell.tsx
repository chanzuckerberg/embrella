import React, { useState } from 'react';
import { CellContext } from '@tanstack/react-table';
import { EntityDataTypes } from '@app/common/types/tableState';
import { Typography } from '@mui/material';
import { Button, LoadingIndicator, DialogTitle, DialogContent, Dialog } from '@czi-sds/components';
import { TomogramData } from './types';
import { DJANGO_URL } from '@app/common/constants/api';

const renderParameterValue = (value: unknown): React.ReactNode => {
  if (typeof value !== 'object' || value === null) {
    return String(value);
  }
  if (Array.isArray(value)) {
    return `[${value.join(', ')}]`;
  }
  return (
    <pre style={{ margin: 0, fontFamily: 'monospace', fontSize: 14, paddingLeft: 8 }}>
      {JSON.stringify(value, null, 2)}
    </pre>
  );
};

export const ParametersCell = (props: CellContext<EntityDataTypes, unknown>) => {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<Record<string, unknown> | string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const rowData = props.row.original as TomogramData | undefined;
  if (!rowData || typeof rowData !== 'object') return <span />;

  const sessionName = rowData.msiSession?.name || '';
  const runNumber = rowData.tomograms?.name || '';
  // If procPlan.name is 'czii-denoise', render nothing
  if (rowData.procPlan?.name === 'czii-denoise') return <span />;
  // Extract only digits for run_id
  const runIdMatch = runNumber.match(/\d+/);
  const runId = runIdMatch ? runIdMatch[0] : '';

  if (!sessionName || !runId) return <span />;

  const workflowUrl = `${DJANGO_URL}/workflow/get_aretomo3?session=${encodeURIComponent(sessionName)}&run_id=${encodeURIComponent(runId)}`;

  const handleOpen = async () => {
    setOpen(true);
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const response = await fetch(workflowUrl, { credentials: 'include' });
      if (!response.ok) throw new Error(`Error: ${response.status} ${response.statusText}`);
      const text = await response.text();
      // Try to parse as JSON, fallback to text
      try {
        setData(JSON.parse(text));
      } catch {
        setData(text);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const shouldShowData = !loading && !error && data !== null && data !== '';
  const isObject = typeof data === 'object' && data !== null;

  return (
    <>
      <Button sdsType="secondary" sdsStyle="outline" onClick={handleOpen}>
        Parameters
      </Button>
      <Dialog onClose={() => setOpen(false)} open={open} sdsSize="l" aria-labelledby="parameters-dialog-title">
        <DialogTitle title="Workflow Parameters" onClose={() => setOpen(false)} data-testid="dialog-title" />
        <DialogContent data-testid="dialog-content" sx={{ minHeight: '400px' }}>
          {loading && <LoadingIndicator sdsStyle="tag" />}
          {Boolean(error) && <Typography color="error">{error}</Typography>}
          {shouldShowData &&
            (isObject ? (
              <table
                style={{
                  width: '100%',
                  fontFamily: 'monospace',
                  fontSize: 14,
                  background: '#fff',
                  borderCollapse: 'collapse',
                }}
              >
                <tbody>
                  {Object.entries(data as Record<string, unknown>).map(([key, value]) => (
                    <tr key={key}>
                      <td
                        style={{
                          fontWeight: 'bold',
                          border: '1px solid #eee',
                          padding: '4px 8px',
                          verticalAlign: 'top',
                          background: '#f7f7f7',
                        }}
                      >
                        {key}
                      </td>
                      <td
                        style={{
                          border: '1px solid #eee',
                          padding: '4px 8px',
                          background: '#fafafa',
                          verticalAlign: 'top',
                        }}
                      >
                        {renderParameterValue(value)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontFamily: 'monospace', fontSize: 14 }}>
                {data}
              </pre>
            ))}
        </DialogContent>
      </Dialog>
    </>
  );
};
