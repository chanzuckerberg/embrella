import { ApiListResponse } from '@app/common/types/tableState';
import { FiltersList } from '@app/common/types/filter';
import { SEARCH_PARAM_NAME, SearchParamValue } from '@app/common/types/search';
import { GridData } from '@app/components/GridsView/types';
import { FetchResponseInfo, TestFilterCategory } from '@testing/types';
import { getSearchParamFirstValue } from '@testing/utils';

const TEST_SORTABLE_GRID_FIELDS = ['grid', 'cassette', 'project', 'puck', 'user'] as const;

export const GRID_A: GridData = {
  grid: {
    id: 0,
    name: 'foo bar foo baz',
    trashed: false,
    url: 'bazfoobazbazbarbar',
    createdAt: '2024-08-23T21:44:30.881Z',
    updatedAt: null,
  },
  cassette: {
    name: 'bar baz foo foo',
  },
  project: {
    id: 0,
    name: 'baz foo baz baz baz',
    url: 'barfoofoobarbaz',
  },
  puck: {
    name: 'baz foo baz',
  },
  user: {
    id: 0,
    name: 'foo',
  },
  specimen: {
    id: 0,
    name: 'aaa',
    samples: [{ id: 1, name: 'foo baz bar foo', url: 'bazfoobazbazbarbar' }],
  },
  freezingSession: {
    id: 0,
    createdAt: '2024-08-23T21:52:44.539Z',
  },
  screeningSession: 'barbarfoobaz',
  msiSession: [
    {
      id: 0,
      name: 'bar baz',
    },
  ],
  labels: [],
};

export const GRID_B: GridData = {
  grid: {
    id: 1,
    name: 'foo barbarbarbaz',
    trashed: false,
    url: 'foofoobarfoofoo',
    createdAt: '2024-09-11T00:52:55.141Z',
    updatedAt: null,
  },
  cassette: {
    name: 'bar foofoo bar bazbar',
  },
  project: {
    id: 1,
    name: 'barbaz bazbar',
    url: 'bazfoobarfoobarbar',
  },
  puck: {
    name: 'foo bar baz foo barfoofoo',
  },
  user: {
    id: 1,
    name: 'bazbaz bar bazfoo bar',
  },
  specimen: {
    id: 1,
    name: 'aaa',
    samples: [{ id: 1, name: 'bar baz bazfoo bazfoo', url: 'foofoobarbar' }],
  },
  freezingSession: {
    id: 1,
    createdAt: '2024-09-11T00:53:04.340Z',
  },
  screeningSession: 'barbazbazbaz',
  msiSession: [
    {
      id: 1,
      name: 'foo baz baz bazfoobaz',
    },
  ],
  labels: [],
};

export const GRIDS = [GRID_A, GRID_B];

export const TEST_DEFAULT_GRIDS_PAGE_SIZE = 10;

// Workflow/Processor Mock Data
export const MOCK_PROCESSOR_ARETOMO3 = {
  name: 'aretomo3',
  display_name: 'AreTomo3',
  version: '2.2.2_07-11-2025',
  default_cluster: 'czii',
  allowed_clusters: ['czii', 'bruno'],
};

export const MOCK_PROCESSOR_DENOISET = {
  name: 'denoiset',
  display_name: 'DenoisET',
  version: '1.0',
  default_cluster: 'czii',
  allowed_clusters: ['czii'],
};

export const MOCK_PROCESSOR_COPICK = {
  name: 'copick',
  display_name: 'Copick Export',
  version: '1.0',
  default_cluster: 'czii',
  allowed_clusters: ['czii', 'bruno'],
};

export const MOCK_PROCESSORS = [MOCK_PROCESSOR_ARETOMO3, MOCK_PROCESSOR_DENOISET, MOCK_PROCESSOR_COPICK];

export const MOCK_PROCESSOR_SCHEMA = {
  success: true,
  processor: 'aretomo3',
  display_name: 'AreTomo3',
  version: '2.2.2_07-11-2025',
  default_cluster: 'czii',
  allowed_clusters: ['czii', 'bruno'],
  schema: {
    type: 'object',
    properties: {
      pixel_size: {
        type: 'number',
        title: 'Pixel Size',
        description: 'Pixel size in Angstroms',
        minimum: 0.1,
        maximum: 100,
      },
      dose_per_tilt: {
        type: 'number',
        title: 'Dose Per Tilt',
        description: 'Electron dose per tilt in e⁻/Ų',
      },
      tilt_axis_angle: {
        type: 'number',
        title: 'Tilt Axis Angle',
        description: 'Rotation angle in degrees',
        minimum: -180,
        maximum: 180,
      },
      binning: {
        type: 'integer',
        title: 'Binning Factor',
        minimum: 1,
        maximum: 8,
        default: 4,
      },
    },
    required: ['pixel_size', 'dose_per_tilt'],
  },
  slurm_options: {
    partition: 'compute',
    time: '02:00:00',
    ntasks: 1,
    mem: '32G',
  },
};

export const URL_BASE = 'http://localhost:8000';
export const URL_NONEXISTENT = '/nonexistent';
export const URL_GRIDS = '/cryo_grids/v1/grids';
export const URL_FILTERS_LIST = '/cryo_grids/v1/grids/filterlist/';
export const URL_FOO = '/foo';

// Workflow API URLs
export const URL_PROCESSORS = '/workflow/v1/processors/';
export const URL_PROCESSOR_SCHEMA = '/workflow/v1/processors/:processorName/schema/';
export const URL_PROCESSOR_OPTIONS = '/workflow/v1/processors/:processorName/options/';
export const URL_PROCESSOR_DEFAULTS = '/workflow/v1/processors/:processorName/defaults/';
export const URL_PROCESSOR_METADATA = '/workflow/v1/processors/:processorName/metadata/';
export const URL_PROCESSOR_VALIDATE = '/workflow/v1/processors/:processorName/validate/';
export const URL_WORKFLOW_EXECUTE = '/workflow/v1/execution/execute/';

// SSH API URLs
export const URL_SSH_SETUP = '/workflow/v1/ssh/setup_key';
export const URL_SSH_CHECK = '/workflow/v1/ssh/check_setup';

export const FETCH_RESPONSE_FILTERS_LIST: FiltersList<TestFilterCategory> = {
  filters: {
    cassette: [
      {
        name: 'foo bar foobaz baz',
        count: 2,
        selected: false,
      },
    ],
    date: [
      {
        name: 'barfoobaz foobar bazbaz',
        count: 1,
        selected: true,
      },
      {
        name: 'baz bar foofoo bar',
        count: 2,
        selected: false,
      },
    ],
    label: [],
    msiSession: [
      {
        name: 'foo bazfoo barfoobar',
        count: 2,
        selected: false,
      },
    ],
    project: [
      {
        name: 'bar baz foo bazbar',
        count: 3,
        selected: true,
      },
    ],
    puck: [
      {
        name: 'bazbazbaz bar barfoo',
        count: 3,
        selected: true,
      },
      {
        name: 'foobar baz foo',
        count: 2,
        selected: true,
      },
    ],
    sample: [
      {
        name: 'bar bar barbar',
        count: 1,
        selected: false,
      },
    ],
    screeningSession: [
      {
        name: 'foofoo baz foo',
        count: 2,
        selected: false,
      },
    ],
    search: [],
    status: [
      {
        name: 'baz bar foo barbaz',
        count: 2,
        selected: false,
      },
    ],
    user: [
      {
        name: 'foo baz foo bazbar',
        count: 1,
        selected: false,
      },
    ],
  },
};

export const FETCH_RESPONSES: Record<string, FetchResponseInfo> = {
  [URL_NONEXISTENT]: {
    status: 404,
  },
  [URL_GRIDS]: {
    body(url) {
      const responseGrids: GridData[] = GRIDS.slice();

      // Query parameters.
      const searchParamValue = url.searchParams.get(SEARCH_PARAM_NAME.QUERY);
      const values: SearchParamValue[] = JSON.parse(searchParamValue || '[]');

      // Sorting category values "sort" and "asc".
      const asc = getSearchParamFirstValue<boolean>(values, 'asc', 0);
      const sort = getSearchParamFirstValue<string>(values, 'sort', 0);
      const direction = asc ? 1 : -1;
      const sortKey = TEST_SORTABLE_GRID_FIELDS.find((key) => key === sort);
      // Sort grids by the first sort value and direction.
      if (sortKey) {
        responseGrids.sort((a, b) => a[sortKey].name.localeCompare(b[sortKey].name) * direction);
      }
      // Pagination category values "page" and "pageSize".
      const page = getSearchParamFirstValue<number>(values, 'page', 0, 1) as number;
      const pageSize = getSearchParamFirstValue<number>(values, 'pageSize', 0, TEST_DEFAULT_GRIDS_PAGE_SIZE) as number;
      const pageStart = (page - 1) * pageSize;

      const orphans = 3;
      const totalPages =
        responseGrids.length <= pageSize + orphans ? 1 : Math.ceil((responseGrids.length - orphans) / pageSize);
      const responseData: ApiListResponse<GridData> = {
        pagination: {
          page,
          pageSize: pageSize,
          totalPages,
          totalResults: responseGrids.length,
        },
        result: responseGrids.slice(pageStart, pageStart + pageSize),
        sortBy: { asc: true, sort: 'project' },
      };

      return JSON.stringify(responseData);
    },
  },
  [URL_FILTERS_LIST]: {
    body: JSON.stringify(FETCH_RESPONSE_FILTERS_LIST),
  },
  [URL_FOO]: {
    body(url) {
      return JSON.stringify(url.searchParams.get('q') === 'true' ? 'bar' : 'foo');
    },
  },
  // Workflow API endpoints
  [URL_PROCESSORS]: {
    body: JSON.stringify({
      success: true,
      processors: MOCK_PROCESSORS,
    }),
  },
  '/workflow/v1/processors/aretomo3/schema/': {
    body: JSON.stringify(MOCK_PROCESSOR_SCHEMA),
  },
  '/workflow/v1/processors/aretomo3/options/': {
    body: JSON.stringify({
      success: true,
      options: {
        gain_file: [
          { value: '/data/gain_ref_001.mrc', label: 'gain_ref_001.mrc' },
          { value: '/data/gain_ref_002.mrc', label: 'gain_ref_002.mrc' },
        ],
      },
    }),
  },
  '/workflow/v1/processors/aretomo3/defaults/': {
    body: JSON.stringify({
      success: true,
      defaults: {
        pixel_size: 2.5,
        dose_per_tilt: 3.2,
        tilt_axis_angle: 88.5,
        binning: 4,
      },
    }),
  },
  '/workflow/v1/processors/aretomo3/metadata/': {
    body: JSON.stringify({
      success: true,
      metadata: {
        help_text: 'AreTomo3 performs tilt series alignment and reconstruction',
        category: 'Reconstruction',
      },
    }),
  },
  '/workflow/v1/processors/aretomo3/validate/': {
    body: JSON.stringify({
      valid: true,
      errors: [],
    }),
  },
  '/workflow/v1/processors/aretomo3/validate-error/': {
    body: JSON.stringify({
      valid: false,
      errors: [
        { field: 'pixel_size', message: 'Pixel size must be greater than 0' },
        { field: 'dose_per_tilt', message: 'Dose per tilt is required' },
      ],
    }),
  },
  [URL_WORKFLOW_EXECUTE]: {
    body: JSON.stringify({
      success: true,
      execution_id: 123,
      job_id: 'slurm_12345',
      message: 'Workflow submitted successfully',
    }),
  },
  '/workflow/v1/execution/execute-ssh-required/': {
    status: 403,
    body: JSON.stringify({
      success: false,
      error: 'SSH setup required',
      ssh_setup_required: true,
    }),
  },
  // SSH API endpoints
  [URL_SSH_SETUP]: {
    body: JSON.stringify({
      success: true,
      message: 'SSH key setup completed successfully',
      can_connect: true,
    }),
  },
  '/workflow/v1/ssh/setup_key-error': {
    status: 400,
    body: JSON.stringify({
      success: false,
      error: 'Invalid credentials',
      can_connect: false,
    }),
  },
  [URL_SSH_CHECK]: {
    body: JSON.stringify({
      success: true,
      setup_required: false,
    }),
  },
};
