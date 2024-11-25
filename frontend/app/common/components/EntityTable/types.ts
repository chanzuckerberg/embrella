import { LinkCellProps } from "@app/components/TomogramsView/columns";

/*
 * Name of attribute in API response to use for the row ID
 */
export type ApiPrimaryEntityAttribute = "tomograms" | "grid";
export type AccessorReturnType = LinkCellProps | string;
