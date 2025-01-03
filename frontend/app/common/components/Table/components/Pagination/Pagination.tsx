import React from "react";
import { RowData, Table } from "@tanstack/react-table";
import { StyledPagination } from "@app/common/components/Table/components/Pagination/style";

interface PaginationProps<TData extends RowData> {
  dataTestId?: string;
  table: Table<TData>;
}

export const Pagination = <TData extends RowData>({
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
