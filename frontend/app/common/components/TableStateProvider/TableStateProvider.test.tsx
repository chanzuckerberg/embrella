import {
  tableStateReducer,
  TableState,
  TableStateAction,
  TableStateActionTypes,
  UpdateFilterAction,
  UpdatePaginationAction,
  UpdateSortAction,
} from './TableStateProvider';
import { getInitialTableState } from './TableStateProvider';
import { PaginationState, SortingState } from '@tanstack/react-table';

describe('tableStateReducer', () => {
  const initialState: TableState = getInitialTableState();

  it('should return state when action us unkown', () => {
    const action = {
      type: 'UNKOWN_ACTION',
      payload: undefined,
    } as unknown as TableStateAction;
    const newState = tableStateReducer(initialState, action);
    expect(newState).toEqual(initialState);
  });

  describe('UpdateFilter action', () => {
    it('updates filter state with provided category filter', () => {
      const action: UpdateFilterAction = {
        type: TableStateActionTypes.UpdateFilter,
        payload: {
          categoryFilter: { category: 'project', value: ['project1'] },
        },
      };
      const newState = tableStateReducer(initialState, action);
      expect(newState).toEqual({
        ...initialState,
        filterState: { project: ['project1'] },
      });
    });

    it('removes filter from filter state when category filter value is empty', () => {
      const stateWithFilter = {
        ...initialState,
        filterState: { project: ['project1'] },
      };
      const action: UpdateFilterAction = {
        type: TableStateActionTypes.UpdateFilter,
        payload: {
          categoryFilter: { category: 'project', value: [] },
        },
      };
      const newState = tableStateReducer(stateWithFilter, action);

      expect(newState).toEqual({
        ...initialState,
      });
    });
  });

  describe('UpdatePagination action', () => {
    it('updates pagination state using value in payload', () => {
      const action: UpdatePaginationAction = {
        type: TableStateActionTypes.UpdatePagination,
        payload: {
          pagination: { pageIndex: 0, pageSize: 10 },
          updaterOrValue: { pageIndex: 1, pageSize: 10 },
        },
      };
      const newState = tableStateReducer(initialState, action);
      expect(newState.paginationState).toEqual({ pageIndex: 1, pageSize: 10 });
    });

    it('updates pagination state using using updater function in payload', () => {
      // mock updater function - increments current pageIndex by 1
      const updaterOrValue = jest.fn((pagination: PaginationState) => ({
        pageIndex: pagination.pageIndex + 1,
        pageSize: pagination.pageSize,
      }));

      const action: UpdatePaginationAction = {
        type: TableStateActionTypes.UpdatePagination,
        payload: {
          pagination: { pageIndex: 0, pageSize: 10 },
          updaterOrValue,
        },
      };
      const newState = tableStateReducer(initialState, action);

      expect(updaterOrValue).toHaveBeenCalled();
      expect(newState.paginationState).toEqual({ pageIndex: 1, pageSize: 10 });
    });
  });

  describe('UpdateSort action', () => {
    it('updates sort state using value in payload', () => {
      const action: UpdateSortAction = {
        type: TableStateActionTypes.UpdateSort,
        payload: {
          sortBy: [{ id: 'updatedAt', desc: true }],
          updaterOrValue: [{ id: 'updatedAt', desc: false }],
        },
      };
      const newState = tableStateReducer(initialState, action);
      expect(newState.sortState).toEqual([{ id: 'updatedAt', desc: false }]);
    });

    it('updates sort state using updater function in payload', () => {
      // mock updater function - inverts the sorting order of first entry in sortingState
      const updaterOrValue = jest.fn((sortingState: SortingState) => [
        {
          id: sortingState[0].id,
          desc: !sortingState[0].desc,
        },
      ]);
      const action: UpdateSortAction = {
        type: TableStateActionTypes.UpdateSort,
        payload: {
          sortBy: [{ id: 'updatedAt', desc: true }],
          updaterOrValue,
        },
      };
      const newState = tableStateReducer(initialState, action);

      expect(updaterOrValue).toHaveBeenCalled();
      expect(newState.sortState).toEqual([{ id: 'updatedAt', desc: false }]);
    });
  });
});
