import { LinkCellProps } from "@/app/common/components/Table/components/LinkCell/LinkCell";

/*
 * Name of attribute in API response to use for the row ID
 */
export type ApiPrimaryEntityAttribute = "annotations" | "tomograms" | "grid";
export type AccessorReturnType = LinkCellProps | string;
