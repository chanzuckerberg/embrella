import { LinkCellProps } from "@/app/common/components/Table/utils/linkUtils";

/*
 * Name of attribute in API response to use for the row ID
 */
export type ApiPrimaryEntityAttribute = "annotations" | "tomograms" | "grid";
export type AccessorReturnType = LinkCellProps | LinkCellProps[] | string;
