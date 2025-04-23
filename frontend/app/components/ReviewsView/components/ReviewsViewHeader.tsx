import {
  TableDispatchContext,
  TableStateActionTypes,
  TableStateContext,
} from "@app/common/components/TableStateProvider/TableStateProvider";
import { InputSearch } from "@czi-sds/components";
import { useContext, useState } from "react";

export const ReviewsViewHeader = () => {
  const tableState = useContext(TableStateContext);
  const dispatchTableState = useContext(TableDispatchContext);
  const [searchValue, setSearchValue] = useState(
    (tableState.filterState.search ?? "") as string,
  );

  return (
    <div>
      <InputSearch
        value={searchValue}
        onChange={(event) => setSearchValue(event.target.value)}
        handleSubmit={(value) => {
          dispatchTableState({
            payload: {
              categoryFilter: {
                category: "search",
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
    </div>
  );
};
