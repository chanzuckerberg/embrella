import { InputDropdownProps as SDSInputDropdownProps } from "@czi-sds/components";
import { ComplexFilterProps } from "@app/common/components/Filter/common/types";

export const COMPLEX_FILTER_PROPS: Pick<
  ComplexFilterProps,
  "isTriggerChangeOnOptionClick" | "multiple" | "search"
> = {
  isTriggerChangeOnOptionClick: true,
  multiple: true,
  search: true,
};

export const INPUT_DROPDOWN_PROPS: Pick<
  SDSInputDropdownProps,
  "intent" | "sdsStage" | "sdsStyle" | "sdsType" | "state"
> = {
  intent: "default",
  sdsStage: "default",
  sdsStyle: "minimal",
  sdsType: "label",
  state: "default",
};
