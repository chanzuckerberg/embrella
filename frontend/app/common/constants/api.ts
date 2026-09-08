function resolveDjangoUrl(): string {
  if (typeof window === 'undefined') {
    return process.env.DJANGO_URL ?? 'http://localhost:8000';
  }
  // Bare-metal dev only: Next.js dev server on :3000 reaches Django on :8000 directly.
  if (process.env.NODE_ENV === 'development' && window.location.port === '3000') {
    return `http://${window.location.hostname}:8000`;
  }
  // Behind nginx and deployed envs: same origin, nginx proxies /api, /user, etc. to Django.
  return window.location.origin;
}

export const DJANGO_URL = resolveDjangoUrl();

export enum API {
  USER = '/user',
  GRIDS = '/cryo_grids/v1/grids/',
  GRIDS_FILTERS_LIST = '/cryo_grids/v1/grids/filterlist/',
  GRIDS_SEARCH_SUGGESTIONS = '/cryo_grids/v1/grids/search_suggestions/',
  TOMOGRAMS = '/processes/v1/tomograms/',
  TOMOGRAMS_FILTERLIST = '/processes/v1/filterlist/',
  ANNOTATIONS = '/processes/v1/annotations/',
  ANNOTATIONS_FILTERLIST = '/annotations/v1/filterlist/',
  METADATA_SUMMARY = '/workflow/metadata/api/v1/summary/',
  METADATA_VIZ = '/workflow/metadata/api/v1/data/',
  REVIEWS = '/api/reviews/',

  // Storage Explorer (Filesystem Surveys & Directories)
  SURVEYS = '/processes/v1/surveys',
  SURVEY_FILES = '/processes/v1/surveys/:surveyId/files',
  DIRECTORIES = '/processes/v1/directories',
  DIRECTORIES_STATS = '/processes/v1/directories/stats',
  DIRECTORIES_FILTERLIST = '/processes/v1/directories/filterlist',
  DIRECTORY_FILES = '/processes/v1/directories/:directoryId/files',

  // Job Management
  JOBS = '/workflow/v1/jobs/',
  JOBS_FILTERLIST = '/workflow/v1/jobs/filterlist/',
  JOB_LOGS = '/workflow/job_logs/',
  SYNCER_LOGS = '/workflow/v1/jobs/:jobId/syncer_logs/',

  // SSH Setup
  SSH_CHECK_SETUP = '/workflow/v1/ssh/check_setup/',

  // Pipeline Execution
  PROCESSORS = '/workflow/v1/processors/',
  PROCESSOR_SCHEMA = '/workflow/v1/processors/:processorName/schema/',
  PROCESSOR_OPTIONS = '/workflow/v1/processors/:processorName/options/',
  PROCESSOR_DEFAULTS = '/workflow/v1/processors/:processorName/defaults/',
  PROCESSOR_METADATA = '/workflow/v1/processors/:processorName/metadata/',
  PROCESSOR_VALIDATE_SESSION = '/workflow/v1/processors/:processorName/validate-session/',
  PIPELINE_EXECUTE = '/workflow/v1/execution/execute/',
  PIPELINE_PREVIEW = '/workflow/v1/execution/preview/',
  PIPELINE_EXECUTION_STATUS = '/workflow/v1/execution/:executionId/status/',
  PIPELINE_EXECUTION_RUN = '/workflow/v1/execution/run/:runId/',
  PIPELINE_CHECK_DEPENDENCIES = '/workflow/v1/execution/check_dependencies/',
  PIPELINE_LOOKUP_IDS = '/workflow/v1/execution/lookup_ids/',
  PIPELINE_EXECUTION_BY_JOB_ID = '/workflow/v1/execution/by_job_id/:jobId/',

  // Processor-specific endpoints
  PLAN_RUNS = '/workflow/v1/execution/plan_runs/',
  COPICK_RUNS = '/workflow/v1/processors/copick/runs/',
  COPICK_ANNOTATED_COUNT = '/workflow/v1/processors/copick/annotated-count/',
  COPICK_TEMPLATE_MAPS = '/workflow/v1/processors/copick/template_maps/',

  // Session Browser
  SESSION_OVERVIEW = '/tem/v1/session-overview/',
  SESSION_OVERVIEW_FILTERLIST = '/tem/v1/session-overview/filterlist/',

  // Storage Explorer (entity-centric tree). Take a ?cluster=, not a survey id.
  STORAGE_SESSIONS = '/processes/v1/storage-sessions/',
  STORAGE_SESSIONS_FILTERLIST = '/processes/v1/storage-sessions/filterlist/',
  STORAGE_SESSIONS_SUMMARY = '/processes/v1/storage-sessions/summary/',
  STORAGE_DECISIONS = '/processes/v1/storage-decisions/',

  // Session/Run Selection
  MSI_SESSIONS = '/tem/v1/sessions/',
  MSI_SESSIONS_LIST = '/workflow/get_msi_session_list',
  MSI_SESSION_ID = '/workflow/get_msisession_id',

  // Mocked out:
  TEM_SESSIONS = '/api/sessions',
  TEM_SESSION = '/api/sessions/:sessionId',
  REVIEW = '/api/reviews/:reviewId',
  REVIEW_EXPORT = '/api/reviews/:reviewId/export',
  REVIEW_TOMOGRAMS = '/api/reviews/:reviewId/tomograms',
  TOMOGRAM_DETAIL = '/api/reviews/:reviewId/tomograms/:tomogramId',

  // Grid Detail (by ID)
  GRID_DETAIL = '/cryo_grids/v1/grids/grid_id/',

  // Grid Logging
  GRID_LOGGING_USERS = '/api/list/all/users/',
  GRID_LOGGING_PUCKS = '/api/list/pucks/',
  // GRID_LOGGING_PUCK_BYUSER = '/api/list/pucks/?user_id=',
  GRID_LOGGING_PUCK_SLOTINFO = '/api/list/pucks/puck_id/slots/',
  GRID_LOGGING_PUCK_GRIDBOXINFO = '/api/list/pucks/puck_id/grid-box/position_in_puck/',
  GRID_LOGGING_CANES = '/api/list/canes/',
  GRID_LOGGING_PROJECT_LEADERS = '/api/list/project-leaders/',
  GRID_LOGGING_FREEZING_SESSIONS = '/api/list/freezing-sessions/',
  GRID_LOGGING_SPECIMENS = '/api/list/specimens/',
  GRID_LOGGING_DEVICES = '/api/list/freezing-sessions/devices/',
  GRID_LOGGING_SAMPLES = '/api/list/samples/',
  LABELS = '/api/list/labels/',
  GRID_LOGGING_CHOICES = '/api/grid-logging/choices/',
  GRID_BOXES = '/cryo_grids/v1/grid-boxes/',
  STANDARD_SAMPLES = '/cryo_grids/v1/standard-samples/',
  SCREENING_GRIDS = '/cryo_grids/v1/screening-grids/',
  SCREENING_GRIDS_FILTERS_LIST = '/cryo_grids/v1/screening-grids/filterlist/',
  GRID_BOXES_FILTERS_LIST = '/cryo_grids/v1/grid-boxes/filterlist/',
  GRID_BOXES_SEARCH_SUGGESTIONS = '/cryo_grids/v1/grid-boxes/search_suggestions/',
  PUCKS_VIEW = '/cryo_grids/v1/pucks/',
  PUCKS_VIEW_FILTERS_LIST = '/cryo_grids/v1/pucks/filterlist/',
  PUCKS_VIEW_SEARCH_SUGGESTIONS = '/cryo_grids/v1/pucks/search_suggestions/',
  GRID_INVENTORY_COUNTS = '/cryo_grids/v1/counts/',
  GRID_BOX_AVAILABLE_POSITIONS = '/cryo_grids/v1/grid-boxes/available_positions/',

  // Projects
  PROJECTS_LIST = '/projects/project_list/',

  // External Resources (Documentation Links)
  EXTERNAL_RESOURCES = '/api/external-resources/',
  EXTERNAL_RESOURCES_DOC_SPACES = '/api/external-resources/doc_spaces/',
  EXTERNAL_RESOURCES_DOC_PAGES = '/api/external-resources/doc_pages/',
  EXTERNAL_RESOURCES_SYSTEMS = '/api/external-resources/systems/',

  // Deposition
  DEPOSITIONS = '/depositions/v1/depositions/',
  DEPOSITION_DATASETS = '/depositions/v1/datasets/',
  DEPOSITION_SESSIONS = '/depositions/v1/sessions/',
  DEPOSITION_METHOD_LINKS = '/depositions/v1/method-links/',
  PEOPLE = '/people/v1/people/',
  INSTITUTIONS = '/people/v1/institutions/',
}

export enum POST_API {
  CREATE_REVIEW = '/api/reviews/',
  SAVE_REVIEW = '/api/reviews/:reviewId/save',
  COMPLETE_REVIEW = '/api/reviews/:reviewId/complete',
  UPDATE_TOMOGRAM_REVIEW = '/api/reviews/:reviewId/tomograms/:tomogramId',
  CREATE_PUCK = '/api/list/pucks/',
  CREATE_GRID_BOX = '/api/list/pucks/puck_id/grid-box/',
  CREATE_FREEZING_SESSION = '/api/list/freezing-sessions/',
  CREATE_GRID = '/cryo_grids/v1/grids/',
  CREATE_SAMPLE = '/api/list/samples/',
  CREATE_SPECIMEN = '/api/list/specimens/',
  CREATE_PROJECT = '/projects/create_project/',
  UPDATE_GRID_BOX = '/api/list/pucks/grid-box/grid_box_id/update/',
  MOVE_GRID_BOX = '/api/list/pucks/grid-box/grid_box_id/move/',
  MOVE_GRID = '/cryo_grids/v1/grids/grid_id/move/',
  DUPLICATE_GRID = '/cryo_grids/v1/grids/grid_id/duplicate/',
  UPDATE_GRID = '/cryo_grids/v1/grids/grid_id/update/',
  CLIP_ALL_GRIDS = '/cryo_grids/v1/grids/clip-all-in-box/grid_box_id/',
  UPDATE_GRID_LABELS = '/cryo_grids/v1/grids/grid_id/update-labels/',
  CREATE_LABEL = '/api/list/labels/',

  // Storage Explorer (Directories)
  BULK_UPDATE_DIRECTORY_STATUS = '/processes/v1/directories/bulk_update_status',

  // Job Management
  BULK_CANCEL_JOBS = '/workflow/v1/jobs/bulk_cancel/',
  RERUN_SYNCER = '/workflow/v1/jobs/:jobId/rerun_syncer/',

  // SSH Setup
  SSH_SETUP_KEY = '/workflow/v1/ssh/setup_key/',

  // Processor Parameter Validation
  PROCESSOR_VALIDATE = '/workflow/v1/processors/:processorName/validate/',

  // External Resources
  CREATE_EXTERNAL_RESOURCE = '/api/external-resources/',
  UPDATE_EXTERNAL_RESOURCE = '/api/external-resources/:resourceId/',
  // Note: DELETE uses same URL as UPDATE but with DELETE method - see postResource usage
}
