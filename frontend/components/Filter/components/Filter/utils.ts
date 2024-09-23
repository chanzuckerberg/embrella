import {
  AutocompleteOption,
  FILTER_VALUE,
  FilterValue,
} from "@/components/Filter/common/types";

/**
 * Returns an array of filter values from the given selected options.
 * @param options - Selected options.
 * @returns an array of filter values.
 */
export function getFilterValue(
  options: (string | AutocompleteOption)[],
): FilterValue[] {
  return options.map(mapFilterValue);
}

/**
 * Maps the given option to a filter value.
 * @param option - Option.
 * @returns filter value.
 */
export function mapFilterValue(
  option: string | AutocompleteOption,
): FilterValue {
  if (typeof option === "string") return option;
  if (option.name === FILTER_VALUE.UNSPECIFIED) return null;
  return option.name;
}
