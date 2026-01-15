/**
 * External resource types for documentation links (Confluence, Google Drive, Benchling, etc.)
 */

export type ResourceType = 'doc_space' | 'doc_page';

export interface ExternalResource {
  id: number;
  resource_type: ResourceType;
  resource_type_display: string;
  system_name: string;
  name: string;
  url: string;
  metadata?: Record<string, unknown>;
}

export interface ExternalResourceListResponse {
  total_resources_count: number;
  resources: ExternalResource[];
}

export interface DocSpacesResponse {
  count: number;
  doc_spaces: ExternalResource[];
}

export interface DocPagesResponse {
  count: number;
  doc_pages: ExternalResource[];
}

export interface SystemsResponse {
  count: number;
  systems: string[];
}

export interface CreateExternalResourceRequest {
  resource_type: ResourceType;
  system_name: string;
  name: string;
  url: string;
  metadata?: Record<string, unknown>;
}

export interface CreateExternalResourceResponse {
  message: string;
  resource: ExternalResource;
}
