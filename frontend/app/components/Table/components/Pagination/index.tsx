import React from "react";
import { RowData } from "@tanstack/react-table";
import { Props } from "@/app/components/Table/components/Pagination/types";
import { StyledPagination } from "@/app/components/Table/components/Pagination/style";

export const Pagination = <TData extends RowData>({
  dataTestId,
  table,
}: Props<TData>): JSX.Element => {
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
