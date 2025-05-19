import {
  TableDispatchContext,
  TableStateActionTypes,
  TableStateContext,
} from '@app/common/components/TableStateProvider/TableStateProvider';
import { Button, Icon, InputSearch } from '@czi-sds/components';
import Link from 'next/link';
import { useContext, useState } from 'react';

export const ReviewsViewHeader = () => {
  const tableState = useContext(TableStateContext);
  const dispatchTableState = useContext(TableDispatchContext);
  const [searchValue, setSearchValue] = useState((tableState.filterState.search ?? '') as string);

  return (
    <div className="flex justify-between">
      <InputSearch
        value={searchValue}
        onChange={(event) => setSearchValue(event.target.value)}
        handleSubmit={(value) => {
          dispatchTableState({
            payload: {
              categoryFilter: {
                category: 'search',
                value,
              },
            },
            type: TableStateActionTypes.UpdateFilter,
          });
        }}
        variant="outlined"
        placeholder="Search Reviews"
        label="Search Reviews"
        id="search-reviews"
      />
      <Link href="/reviews/create" className="!mt-auto !mb-auto">
        <Button
          sdsStyle="square"
          variant="contained"
          startIcon={<Icon sdsIcon="Plus" sdsSize="xs" />}
          className="h-[32px] !text-[13px] !font-semibold"
        >
          Create Review
        </Button>
      </Link>
    </div>
  );
};
