import {
  AutocompleteOption,
  FILTER_VALUE,
  FilterConfig,
  FilterView,
  SelectFilterView,
} from "@/app/components/Filter/common/types";
import { FilterOption, FiltersList } from "@app/common/types/filter";

/**
 * Build view model of filter groups.
 * @param filterConfigs - Filter configurations.
 * @param filters - Filters list filters.
 * @returns filter groups view model.
 */
export function buildFilterGroups<FilterId, FilterCategory extends string>(
  filterConfigs: FilterConfig<FilterId, FilterCategory>[][],
  filters?: FiltersList<FilterCategory>["filters"]
): FilterView<FilterId, FilterCategory>[][] {
  return filterConfigs.map((configs) => {
    return configs.map((config) => {
      const { filterId, filterCategory, label } = config;
      const filterOptions = filters?.[filterCategory];
      return {
        category: filterCategory,
        disabled: isFilterViewDisabled(filterOptions),
        filterId,
        label,
        options: buildFilterViewOptions(filterOptions),
        value: buildFilterViewValue(filterOptions),
      };
    });
  });
}

/**
 * Build filter view options from the given filter options.
 * @param filterOptions - Filter options.
 * @returns an array of filter view options.
 */
function buildFilterViewOptions<FilterId, FilterCategory extends string>(
  filterOptions?: FilterOption[]
): SelectFilterView<FilterId, FilterCategory>["options"] {
  if (!filterOptions) return [];
  return filterOptions.map(mapOption);
}

/**
 * Build filter view selected values from the given filter options.
 * @param filterOptions - Filter options.
 * @returns an array of selected values.
 */
function buildFilterViewValue<FilterId, FilterCategory extends string>(
  filterOptions?: FilterOption[]
): SelectFilterView<FilterId, FilterCategory>["value"] {
  if (!filterOptions) return [];
  return filterOptions.filter(isSelected).map(mapOption);
}

/**
 * Returns true if the given filter view is disabled.
 * @param filterOptions - Filter options.
 * @returns true if the given filter view is disabled.
 */
function isFilterViewDisabled(filterOptions?: FilterOption[]): boolean {
  if (!filterOptions) return true;
  return filterOptions.length === 0;
}

/**
 * Returns true if the given filter option is selected.
 * @param filterOption - Filter option.
 * @returns true if the given filter option is selected.
 */
function isSelected(filterOption: FilterOption): boolean {
  return filterOption.selected;
}

/**
 * Map filter option to filter view option.
 * @param filterOption - Filter option.
 * @returns filter view option.
 */
function mapOption(filterOption: FilterOption): AutocompleteOption {
  const { count, name, selected } = filterOption;
  return { count, name: sanitizeFilterName(name), selected };
}

/**
 * Sanitize filter name to a valid string value.
 * @param name - Name.
 * @returns sanitized name.
 */
function sanitizeFilterName(name: FilterOption["name"]): string {
  // sanitize null value to unspecified.
  if (name === null) return FILTER_VALUE.UNSPECIFIED;
  // sanitize boolean value to string.
  if (typeof name === "boolean") {
    return name.toString();
  }
  return name;
}
