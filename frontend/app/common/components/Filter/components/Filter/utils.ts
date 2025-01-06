import {
  AutocompleteOption,
  FILTER_VALUE,
} from "@app/common/components/EntityTableFilters/types";
import { FilterValue } from "@app/common/types/filter";

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
  return sanitizeFilterValue(option.name);
}

/**
 * Sanitize filter name to a valid filter value.
 * @param name - Filter option's name.
 * @returns sanitized filter value.
 */
export function sanitizeFilterValue(name: string): FilterValue {
  if (name === FILTER_VALUE.UNSPECIFIED) return null;
  if (name === FILTER_VALUE.FALSE) return false;
  if (name === FILTER_VALUE.TRUE) return true;
  return name;
}
