import { CategoryFilter, FilterState } from "@/components/Filter/common/types";
import { FilterOption, FiltersList } from "@/common/types";

/**
 * Build the current set of selected filters.
 * @param filtersList - Filters list.
 * @returns current filter state.
 */
export function buildCurrentFilterState<FilterCategory extends string>(
  filtersList?: FiltersList<FilterCategory>,
): FilterState<FilterCategory> {
  const filterState = {} as FilterState<FilterCategory>;
  if (filtersList) {
    for (const [category, filterOptions] of Object.entries(
      filtersList.filters,
    ) as [FilterCategory, FilterOption[]][]) {
      const selectedValues = filterOptions.filter(isSelected).map(mapValue);
      if (selectedValues.length > 0) {
        Object.assign(filterState, { [category]: selectedValues });
      }
    }
  }
  return filterState;
}

/**
 * Build updated set of selected filters for the given selected category and the selected category values.
 * @param categoryFilter - Selected category and category values.
 * @param filtersList - Filters list.
 * @returns updated filter state.
 */
export function buildNextFilterState<FilterCategory extends string>(
  categoryFilter: CategoryFilter<FilterCategory>,
  filtersList?: FiltersList<FilterCategory>,
): FilterState<FilterCategory> {
  const { category, value } = categoryFilter;
  // Grab the current filter state.
  const currentFilters = buildCurrentFilterState(filtersList);
  // Clone current filter state.
  const nextFilters: FilterState<FilterCategory> = { ...currentFilters };
  if (value.length > 0) {
    // Update filter state with category and selected values.
    Object.assign(nextFilters, { [category]: value });
  } else {
    // Remove the category from the filter state if no values are selected.
    delete nextFilters[category];
  }
  return nextFilters;
}

/**
 * Returns true if the given filter option is selected.
 * @param filterOption - Filter option.
 * @returns true if the filter option is selected.
 */
function isSelected(filterOption: FilterOption): boolean {
  return filterOption.selected;
}

/**
 * Maps the given filter option to a filter value.
 * @param filterOption - Filter option.
 * @returns filter value.
 */
function mapValue(filterOption: FilterOption): FilterOption["name"] {
  return filterOption.name;
}
