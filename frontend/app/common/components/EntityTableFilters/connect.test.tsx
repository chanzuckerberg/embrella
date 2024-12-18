import { renderHook, act } from "@testing-library/react";

import { useConnect } from "./connect";
import {
  TableDispatchContext,
  TableStateContext,
} from "@app/common/components/TableStateProvider/TableStateProvider";
import { TableStateActionTypes } from "@app/common/components/TableStateProvider/TableStateProvider";
import {
  EntityFilterCategories,
  EntityFilterConfigs,
} from "@app/common/types/filter";
import { useFilterList } from "@app/common/components/Filter/hooks/useFilterList/useFilterList";
import { API } from "@app/common/constants/api";
import { useFetchFilters } from "@app/common/hooks/useFetchFilters/useFetchFilters";

jest.mock("../../hooks/useFetchFilters/useFetchFilters", () => ({
  useFetchFilters: jest.fn(),
}));

jest.mock("../Filter/hooks/useFilterList/useFilterList", () => ({
  useFilterList: jest.fn(),
}));

const mockDispatch = jest.fn();
const mockState = {
  filterState: {},
  paginationState: { pageIndex: 0, pageSize: 10 },
  sortState: [],
};

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <TableDispatchContext.Provider value={mockDispatch}>
    <TableStateContext.Provider value={mockState}>
      {children}
    </TableStateContext.Provider>
  </TableDispatchContext.Provider>
);

describe("useConnect", () => {
  let filtersList: any;
  let filters: any;
  let entityFilterConfigs: EntityFilterConfigs[][];

  beforeEach(() => {
    filtersList = {
      filters: {
        project: [
          {
            name: "BD01",
            count: 7,
            selected: false,
          },
          {
            name: "BD01 copy",
            count: 4,
            selected: false,
          },
        ],
      },
    };

    filters = [
      [
        {
          category: "project",
          disabled: false,
          filterId: "PROJECT",
          label: "Project",
          options: [
            {
              count: 7,
              name: "BD01",
              selected: false,
            },
            {
              count: 4,
              name: "BD01 copy",
              selected: false,
            },
          ],
          value: [],
        },
      ],
    ];

    entityFilterConfigs = [
      [
        {
          filterCategory: "project",
          filterId: "PROJECT",
          label: "Project",
        } as EntityFilterConfigs,
      ],
    ];
  });

  it("should call useFilterList with correct arguments", () => {
    (useFetchFilters as jest.Mock).mockReturnValue(filtersList);
    (useFilterList as jest.Mock).mockReturnValue(filters);

    const { result } = renderHook(
      () => useConnect(entityFilterConfigs, API.TOMOGRAMS_FILTERLIST_V1),
      { wrapper },
    );

    expect(useFetchFilters).toHaveBeenCalledWith("/processes/v1/filterlist", {
      q: [],
    });

    expect(useFilterList).toHaveBeenCalledWith(
      entityFilterConfigs,
      filtersList,
    );
    expect(result.current.filters).toBe(filters);
  });

  it("should dispatch UpdateFilterAction on filter change", () => {
    (useFilterList as jest.Mock).mockReturnValue(filtersList);

    const { result } = renderHook(
      () => useConnect(entityFilterConfigs, API.TOMOGRAMS_FILTERLIST_V1),
      { wrapper },
    );

    const categoryFilter = {
      category: "user" as EntityFilterCategories,
      value: ["someUser"],
    };

    act(() => {
      result.current.onFilter(categoryFilter);
    });

    expect(mockDispatch).toHaveBeenCalledWith({
      type: TableStateActionTypes.UpdateFilter,
      payload: {
        categoryFilter,
      },
    });
  });
});
