/*
 * Name of attribute in API response to use for the row ID
 */
export type ApiPrimaryEntityAttribute = 'annotations' | 'tomograms' | 'grid' | 'review' | 'job';
export type AccessorReturnType = LinkCellProps | LinkCellProps[] | string;

export interface LinkCellProps {
  children: string;
  href: string;
}
