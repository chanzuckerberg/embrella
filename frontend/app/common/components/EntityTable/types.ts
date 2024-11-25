import { LinkCellProps } from "@app/components/Table/components/LinkCell/LinkCell";

/*
 * Name of attribute in API response to use for the row ID
 */
export type ApiPrimaryEntityAttribute = "tomograms" | "grid";
export type AccessorReturnType = LinkCellProps | string;
