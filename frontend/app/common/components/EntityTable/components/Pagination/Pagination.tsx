import React from "react";
import { Table } from "@tanstack/react-table";
import { StyledPagination } from "@app/common/components/EntityTable/components/Pagination/style";
import { EntityDataTypes } from "@app/common/types/tableState";

interface PaginationProps<TData extends EntityDataTypes> {
  dataTestId?: string;
  table: Table<TData>;
}

export const Pagination = <TData extends EntityDataTypes>({
  dataTestId,
  table,
}: PaginationProps<TData>): JSX.Element => {
  const { getRowCount, getState, nextPage, previousPage, setPageIndex } = table;
  const {
    pagination: { pageIndex, pageSize },
  } = getState();
  return (
    <StyledPagination
      currentPage={pageIndex + 1}
      data-testid={dataTestId}
      onNextPage={nextPage}
      onPageChange={(page) => setPageIndex(page - 1)}
      onPreviousPage={previousPage}
      pageSize={pageSize}
      totalCount={getRowCount()}
      truncateDropdown
    />
  );
};
