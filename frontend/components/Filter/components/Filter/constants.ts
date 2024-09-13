import { InputDropdownProps as SDSInputDropdownProps } from "@czi-sds/components";
import { ComplexFilterProps } from "@/components/Filter/common/types";

export const COMPLEX_FILTER_PROPS: Pick<
  ComplexFilterProps,
  "isTriggerChangeOnOptionClick" | "multiple"
> = {
  isTriggerChangeOnOptionClick: true,
  multiple: true,
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
