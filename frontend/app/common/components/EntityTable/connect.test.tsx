import { getRowId, useConnect } from './connect';
import { TableDispatchContext, TableStateContext } from '@app/common/components/TableStateProvider/TableStateProvider';
import { API } from '@app/common/constants/api';
import { EntityAPIPrimaryAttributeToDataType } from '@app/common/types/entity';
import { EntityDataTypes } from '@app/common/types/tableState';
import { AnnotationData } from '@app/components/AnnotationsView/types';
import { GridData } from '@app/components/GridsView/types';
import { SessionOverviewData } from '@app/components/SessionBrowserView/types';
import { TomogramData } from '@app/components/TomogramsView/types';
import { act, renderHook } from '@testing-library/react';

jest.mock('../../hooks/useFetchTableData/useFetchTableData', () => ({
  useFetchTableData: jest.fn(),
}));

describe('getRowId', () => {
  it('should return the correct row ID for a tomogram entity', () => {
    const row: EntityDataTypes = {
      tomograms: {
        id: 123,
      },
    } as TomogramData;

    const entityApiResponseField: keyof EntityAPIPrimaryAttributeToDataType = 'tomograms';
    const rowId = getRowId(row, entityApiResponseField);

    expect(rowId).toBe('123');
  });

  it('should return the correct row ID for a grid entity', () => {
    const row: EntityDataTypes = {
      grid: { id: 456 },
    } as GridData;

    const entityApiResponseField: keyof EntityAPIPrimaryAttributeToDataType = 'grid';
    const rowId = getRowId(row, entityApiResponseField);

    expect(rowId).toBe('456');
  });

  it('should return the correct row ID for an annotation entity', () => {
    const row: EntityDataTypes = {
      annotations: { id: 789 },
    } as AnnotationData;

    const entityApiResponseField: keyof EntityAPIPrimaryAttributeToDataType = 'annotations';
    const rowId = getRowId(row, entityApiResponseField);

    expect(rowId).toBe('789');
  });

  it('should return the correct row ID for a session entity', () => {
    const row: EntityDataTypes = {
      session: { id: 321, name: '24mar01a' },
    } as SessionOverviewData;

    const entityApiResponseField: keyof EntityAPIPrimaryAttributeToDataType = 'session';
    const rowId = getRowId(row, entityApiResponseField);

    expect(rowId).toBe('321');
  });

  it('should fall back to the namespaced id for a session run sub-row', () => {
    // Run sub-rows carry no `session`, and their bare ids ("run-311") are
    // namespaced so session 311 and run 311 cannot collide on one row key.
    const row = { id: 'run-311' } as unknown as EntityDataTypes;

    expect(getRowId(row, 'session')).toBe('run-311');
  });
});

describe('useConnect', () => {
  const mockDispatch = jest.fn();
  const mockState = {
    filterState: {},
    paginationState: { pageIndex: 0, pageSize: 10 },
    sortState: [],
  };

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <TableDispatchContext.Provider value={mockDispatch}>
      <TableStateContext.Provider value={mockState}>{children}</TableStateContext.Provider>
    </TableDispatchContext.Provider>
  );

  it('should set up table options correctly', () => {
    const { result } = renderHook(() => useConnect(API.TOMOGRAMS, 'tomograms', []), { wrapper });

    expect(result.current.table).toBeDefined();
  });

  it('should dispatch UpdatePagination action on pagination change', () => {
    const { result } = renderHook(() => useConnect(API.TOMOGRAMS, 'tomograms', []), { wrapper });

    act(() => {
      result.current.table.setPageIndex(1);
    });

    expect(mockDispatch).toHaveBeenCalledWith({
      type: 'UPDATE_PAGINATION_ACTION',
      payload: {
        pagination: { pageIndex: 0, pageSize: 10 },
        updaterOrValue: expect.any(Function),
      },
    });
  });

  it('should dispatch UpdateSort action on sorting change', () => {
    const { result } = renderHook(() => useConnect(API.TOMOGRAMS, 'tomograms', []), { wrapper });

    act(() => {
      result.current.table.setSorting([{ id: 'name', desc: false }]);
    });

    expect(mockDispatch).toHaveBeenCalledWith({
      type: 'UPDATE_SORT_ACTION',
      payload: {
        sortBy: [],
        updaterOrValue: [{ id: 'name', desc: false }],
      },
    });
  });
});
