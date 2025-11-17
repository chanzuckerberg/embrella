/* eslint-disable sonarjs/no-duplicate-string */

export const DJANGO_URL =
  typeof window !== 'undefined'
    ? window.location.hostname === 'localhost'
      ? 'http://localhost:8000' // Local Django server.
      : window.location.origin // Deployed envs use same origin for both Django and Next.
    : (process.env.DJANGO_URL ?? 'http://localhost:8000');

export enum API {
  USER = '/user',
  GRIDS = '/cryo_grids/v1/grids',
  GRIDS_FILTERS_LIST = '/cryo_grids/v1/filterlist',
  TOMOGRAMS = '/processes/v1/tomograms',
  TOMOGRAMS_FILTERLIST = '/processes/v1/filterlist',
  ANNOTATIONS = '/processes/v1/annotations',
  ANNOTATIONS_FILTERLIST = '/annotations/v1/filterlist',
  METADATA_SUMMARY = '/workflow/metadata/api/v1/summary',
  METADATA_VIZ = '/workflow/metadata/api/v1/data',
  REVIEWS = '/api/reviews/',

  // Mocked out:
  TEM_SESSIONS = '/api/sessions',
  TEM_SESSION = '/api/sessions/:sessionId',
  REVIEW = '/api/reviews/:reviewId',
  REVIEW_EXPORT = '/api/reviews/:reviewId/export',
  REVIEW_TOMOGRAMS = '/api/reviews/:reviewId/tomograms',
  TOMOGRAM_DETAIL = '/api/reviews/:reviewId/tomograms/:tomogramId',

  // Grid Logging
  GRID_LOGGING_USERS = '/api/list/all/users',
  GRID_LOGGING_PROJECT_LEADERS = '/api/list/project-leaders',
  GRID_LOGGING_PUCKS = '/api/list/pucks',
  // GRID_LOGGING_PUCK_BYUSER = '/api/list/pucks/?user_id=',
  GRID_LOGGING_PUCK_SLOTINFO = '/api/list/pucks/puck_id/slots/',
  GRID_LOGGING_PUCK_GRIDBOXINFO = '/api/list/pucks/puck_id/grid-box/position_in_puck/',
  GRID_LOGGING_GRID_DETAILS = '/api/list/pucks/puck_id/grid-box/position_in_puck/grid/grid_id/',
  //http://127.0.0.1:8000/api/list/pucks/22/grid-box/2/grid/36/
  GRID_LOGGING_CHOICES = '/api/grid-logging/choices/',
  GRID_LOGGING_CANES = '/api/list/canes/',
  GRID_LOGGING_SPECIMENS = '/api/list/specimens/',
  GRID_LOGGING_SAMPLES = '/api/list/samples/',
  GRID_LOGGING_FREEZING_SESSIONS = '/api/list/freezing-sessions/',
  GRID_LOGGING_DEVICES = '/api/list/freezing-sessions/devices/',
  GRID_LOGGING_CONFLUENCE_SPACES = '/api/list/confluence-spaces/',
  GRID_LOGGING_DRIVE_FOLDERS = '/api/list/drive-folders/',
  GRID_LOGGING_CONFLUENCE_PAGES = '/api/list/confluence-pages/',


  // Projects
  PROJECTS_LIST = '/projects/project_list/',
}

export enum POST_API {
  CREATE_REVIEW = '/api/reviews/',
  SAVE_REVIEW = '/api/reviews/:reviewId/save',
  COMPLETE_REVIEW = '/api/reviews/:reviewId/complete',
  UPDATE_TOMOGRAM_REVIEW = '/api/reviews/:reviewId/tomograms/:tomogramId',
  CREATE_PUCK = '/api/list/pucks/',
  CREATE_GRID_BOX = '/api/list/pucks/puck_id/grid-box/',
  CREATE_GRID = '/api/list/grids/',
  CLIP_ALL_GRIDS = '/api/list/grids/clip-all-in-box/grid_box_id/',
  MOVE_GRID_BOX = '/api/list/pucks/grid-box/grid_box_id/move/',
  MOVE_GRID = '/api/list/grids/grid_id/move/',
  CREATE_FREEZING_SESSION = '/api/list/freezing-sessions/',
  CREATE_PROJECT = '/projects/create_project/',
  CREATE_SAMPLE = '/api/list/samples/',
  CREATE_SPECIMEN = '/api/list/specimens/',
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const MOCKED_APIS: Partial<Record<API, any>> = {
  // [API.REVIEWS]: (url: string) => {
  //   let reviews = [
  //     {
  //       review: {
  //         id: 123456,
  //         name: 'Tomogram Quality - 24nov10 - run001 - denoised',
  //         url: '/api/reviews/rev_abcdef123456',
  //         type: 'tomogram_quality',
  //         annotationObjects: ['ribosome', 'mitochondrion'],
  //       },
  //       session: {
  //         id: 24110,
  //         name: 'Grid6_2025-04-22',
  //         url: '/api/sessions/24nov10',
  //       },
  //       updatedAt: '2025-04-22T15:20:00Z',
  //       status: 'in_progress',
  //       reviewedCount: 45,
  //       totalCount: 100,
  //       reviewer: {
  //         id: 1,
  //         name: 'Yue Yu',
  //         url: '/api/users/101',
  //       },
  //     },
  //     {
  //       review: {
  //         id: 456789,
  //         name: 'Tomogram Quality - 24oct30 - run001 - DCTF',
  //         url: '/api/reviews/rev_456789abcdef',
  //         type: 'tomogram_quality',
  //         annotationObjects: ['nucleus', 'cytosolic ribosome'],
  //       },
  //       session: {
  //         id: 24030,
  //         name: 'Grid5_2025-04-08',
  //         url: '/api/sessions/24oct30',
  //       },
  //       runId: 'run001',
  //       updatedAt: '2025-04-18T10:15:00Z',
  //       status: 'complete',
  //       reviewedCount: 84,
  //       totalCount: 84,
  //       reviewer: {
  //         id: 1,
  //         name: 'Bryan Chu',
  //         url: '/api/users/102',
  //       },
  //     },
  //     {
  //       review: {
  //         id: 654321,
  //         name: 'Tomogram Quality - Grid4_TestRun - run002 - Denoised',
  //         url: '/api/reviews/rev_fedcba654321',
  //         type: 'tomogram_quality',
  //         annotationObjects: ['lysosome', 'golgi apparatus'],
  //       },
  //       session: {
  //         id: 4321,
  //         name: 'Grid4_TestRun',
  //         url: '/api/sessions/session_4321',
  //       },
  //       runId: 'run002',
  //       updatedAt: '2025-04-15T14:30:00Z',
  //       status: 'not_started',
  //       reviewedCount: 0,
  //       totalCount: 20,
  //       reviewer: {
  //         id: 103,
  //         name: 'John Doe',
  //         url: '/api/users/103',
  //       },
  //     },
  //     {
  //       review: {
  //         id: 789012,
  //         name: 'Segmentation Labeling - 24nov10 - run001',
  //         url: '/api/reviews/rev_789012ghijkl',
  //         type: 'segmentation_labeling',
  //         annotationObjects: ['actin filament', 'microtubule'],
  //       },
  //       session: {
  //         id: 24110,
  //         name: 'Grid6_2025-04-22',
  //         url: '/api/sessions/24nov10',
  //       },
  //       runId: 'run001',
  //       updatedAt: '2025-04-21T11:45:00Z',
  //       status: 'in_progress',
  //       reviewedCount: 30,
  //       totalCount: 100,
  //       reviewer: {
  //         id: 101,
  //         name: 'Yue Yu',
  //         url: '/api/users/101',
  //       },
  //     },
  //     {
  //       review: {
  //         id: 890123,
  //         name: 'Tomogram Quality - 24dec15 - run001 - SART',
  //         url: '/api/reviews/rev_89012345mnop',
  //         type: 'tomogram_quality',
  //         annotationObjects: ['nuclear envelope', 'chromatin'],
  //       },
  //       session: {
  //         id: 24215,
  //         name: 'Grid7_2025-04-10',
  //         url: '/api/sessions/24dec15',
  //       },
  //       runId: 'run001',
  //       updatedAt: '2025-04-10T14:30:00Z',
  //       status: 'complete',
  //       reviewedCount: 65,
  //       totalCount: 65,
  //       reviewer: {
  //         id: 104,
  //         name: 'Emma Wilson',
  //         url: '/api/users/104',
  //       },
  //     },
  //     {
  //       review: {
  //         id: 901234,
  //         name: 'Segmentation Labeling - Grid7_2025-04-10 - run002',
  //         url: '/api/reviews/rev_90123456qrst',
  //         type: 'segmentation_labeling',
  //         annotationObjects: ['endoplasmic reticulum', 'peroxisome'],
  //       },
  //       session: {
  //         id: 24215,
  //         name: 'Grid7_2025-04-10',
  //         url: '/api/sessions/24dec15',
  //       },
  //       runId: 'run002',
  //       updatedAt: '2025-04-12T09:45:00Z',
  //       status: 'in_progress',
  //       reviewedCount: 42,
  //       totalCount: 70,
  //       reviewer: {
  //         id: 105,
  //         name: 'Michael Chen',
  //         url: '/api/users/105',
  //       },
  //     },
  //     {
  //       review: {
  //         id: 112233,
  //         name: 'Particle Picking - Grid5_2025-04-08 - run001',
  //         url: '/api/reviews/rev_112233uvwx',
  //         type: 'particle_picking',
  //         annotationObjects: ['vesicle', 'plasma membrane'],
  //       },
  //       session: {
  //         id: 24030,
  //         name: 'Grid5_2025-04-08',
  //         url: '/api/sessions/24oct30',
  //       },
  //       runId: 'run001',
  //       updatedAt: '2025-04-20T16:20:00Z',
  //       status: 'not_started',
  //       reviewedCount: 0,
  //       totalCount: 50,
  //       reviewer: {
  //         id: 106,
  //         name: 'Sarah Johnson',
  //         url: '/api/users/106',
  //       },
  //     },
  //     {
  //       review: {
  //         id: 445566,
  //         name: 'Tomogram Quality - 25jan05 - run001 - Denoised',
  //         url: '/api/reviews/rev_445566yzab',
  //         type: 'tomogram_quality',
  //         annotationObjects: ['ribosome', 'mitochondrion'],
  //       },
  //       session: {
  //         id: 25005,
  //         name: 'Grid8_2025-01-05',
  //         url: '/api/sessions/25jan05',
  //       },
  //       runId: 'run001',
  //       updatedAt: '2025-01-06T11:10:00Z',
  //       status: 'in_progress',
  //       reviewedCount: 120,
  //       totalCount: 120,
  //       reviewer: {
  //         id: 1,
  //         name: 'Bryan Chu',
  //         url: '/api/users/102',
  //       },
  //     },
  //     {
  //       review: {
  //         id: 778899,
  //         name: 'Tomogram Quality - 25feb20 - run003 - DCTF',
  //         url: '/api/reviews/rev_778899cdef',
  //         type: 'tomogram_quality',
  //         annotationObjects: ['nucleus', 'cytosolic ribosome'],
  //       },
  //       session: {
  //         id: 25220,
  //         name: 'Grid9_2025-02-20',
  //         url: '/api/sessions/25feb20',
  //       },
  //       runId: 'run003',
  //       updatedAt: '2025-02-22T08:30:00Z',
  //       status: 'in_progress',
  //       reviewedCount: 48,
  //       totalCount: 95,
  //       reviewer: {
  //         id: 107,
  //         name: 'Alex Roberts',
  //         url: '/api/users/107',
  //       },
  //     },
  //     {
  //       review: {
  //         id: 224466,
  //         name: 'Particle Picking - Grid9_2025-02-20 - run002',
  //         url: '/api/reviews/rev_224466ghij',
  //         type: 'particle_picking',
  //         annotationObjects: ['lysosome', 'golgi apparatus'],
  //       },
  //       session: {
  //         id: 25220,
  //         name: 'Grid9_2025-02-20',
  //         url: '/api/sessions/25feb20',
  //       },
  //       runId: 'run002',
  //       updatedAt: '2025-03-01T14:15:00Z',
  //       status: 'complete',
  //       reviewedCount: 80,
  //       totalCount: 80,
  //       reviewer: {
  //         id: 103,
  //         name: 'John Doe',
  //         url: '/api/users/103',
  //       },
  //     },
  //     {
  //       review: {
  //         id: 335577,
  //         name: 'Segmentation Labeling - 25mar15 - run001',
  //         url: '/api/reviews/rev_335577klmn',
  //         type: 'segmentation_labeling',
  //         annotationObjects: ['actin filament', 'microtubule'],
  //       },
  //       session: {
  //         id: 25315,
  //         name: 'Grid10_2025-03-15',
  //         url: '/api/sessions/25mar15',
  //       },
  //       runId: 'run001',
  //       updatedAt: '2025-03-18T10:45:00Z',
  //       status: 'not_started',
  //       reviewedCount: 0,
  //       totalCount: 110,
  //       reviewer: {
  //         id: 108,
  //         name: 'Jessica Kim',
  //         url: '/api/users/108',
  //       },
  //     },
  //     {
  //       review: {
  //         id: 998877,
  //         name: 'Tomogram Quality - 25apr01 - run001 - SART',
  //         url: '/api/reviews/rev_998877opqr',
  //         type: 'tomogram_quality',
  //         annotationObjects: ['nuclear envelope', 'chromatin'],
  //       },
  //       session: {
  //         id: 25401,
  //         name: 'Grid11_2025-04-01',
  //         url: '/api/sessions/25apr01',
  //       },
  //       runId: 'run001',
  //       updatedAt: '2025-04-05T09:20:00Z',
  //       status: 'in_progress',
  //       reviewedCount: 25,
  //       totalCount: 75,
  //       reviewer: {
  //         id: 101,
  //         name: 'Yue Yu',
  //         url: '/api/users/101',
  //       },
  //     },
  //   ];

  //   let params: SearchParamValue[] = [];
  //   if (url.includes('q=')) {
  //     try {
  //       params = JSON.parse(decodeURIComponent(url.split('q=')[1]));
  //       const searchParam = params.find((param) => param.category === 'search');
  //       const pageParam = params.find((param) => param.category);
  //       if (searchParam !== undefined) {
  //         reviews = reviews.filter((review) => review.review.name.includes(searchParam.value as string));
  //       } else if (pageParam !== undefined) {
  //         reviews = reviews.slice(0, 10);
  //       }
  //     } catch (e) {
  //       console.log(e);
  //       console.log(`Mock function failed to parse ${url}`);
  //     }
  //   }

  //   return {
  //     result: reviews,
  //     pagination: {
  //       page: 1,
  //       pageSize: 10,
  //       totalPages: 2,
  //       totalResults: 12,
  //     },
  //     sortBy: {
  //       sort: 'updatedAt',
  //       asc: false,
  //     },
  //   };
  // },
  // [API.TEM_SESSIONS]: [
  //   {
  //     sessionId: '24oct30',
  //     sessionName: 'Grid5_2025-04-08',
  //     createdAt: '2025-04-08T13:22:00Z',
  //     projectName: 'Project A',
  //     savePath: '/mnt/data/tomograms/2025-04-08/Grid5',
  //     runs: [
  //       {
  //         runId: 'run001',
  //         numTomograms: 84,
  //         reconstructionTypes: ['DCTF', 'Denoised', 'SART'],
  //       },
  //     ],
  //   },
  //   {
  //     sessionId: '24nov10',
  //     sessionName: 'Grid6_2025-04-22',
  //     createdAt: '2025-04-22T09:10:00Z',
  //     projectName: 'Project B',
  //     savePath: '/mnt/data/tomograms/2025-04-22/Grid6',
  //     runs: [
  //       {
  //         runId: 'run001',
  //         numTomograms: 100,
  //         reconstructionTypes: ['DCTF', 'Denoised', 'SART'],
  //       },
  //     ],
  //   },
  //   {
  //     sessionId: 'session_4321',
  //     sessionName: 'Grid4_TestRun',
  //     createdAt: '2025-04-01T09:10:00Z',
  //     projectName: 'Project C',
  //     savePath: '/mnt/data/tomograms/2025-04-01/Grid4_TestRun',
  //     runs: [
  //       {
  //         runId: 'run001',
  //         numTomograms: 20,
  //         reconstructionTypes: ['DCTF', 'SART'],
  //       },
  //       {
  //         runId: 'run002',
  //         numTomograms: 20,
  //         reconstructionTypes: ['Denoised'],
  //       },
  //     ],
  //   },
  // ],
  [API.TEM_SESSION]: {
    sessionId: '24nov10',
    sessionName: 'Grid6_2025-04-22',
    createdAt: '2025-04-22T09:10:00Z',
    savePath: '/mnt/data/tomograms/2025-04-22/Grid6',
    metadata: {
      microscope: 'Titan Krios',
      operator: 'Yue Yu',
      project: 'SARS-CoV-2',
    },
    runs: [
      {
        runId: 'run001',
        numTomograms: 100,
        reconstructionTypes: ['DCTF', 'Denoised', 'SART'],
      },
    ],
  },
  // [API.REVIEW]: (url: string) => {
  //   const reviewId = url.split('/').pop();
  //   const reviewsObj = MOCKED_APIS[API.REVIEWS]('');
  //   const reviews = reviewsObj.result;
  //   const review = reviews.find((r: { review: { id: number } }) => String(r.review.id) === String(reviewId));

  //   return {
  //     reviewId: review?.review.id,
  //     reviewName: review?.review.name,
  //     owner: {
  //       id: review?.reviewer.id,
  //       name: review?.reviewer.name,
  //       url: review?.reviewer.url,
  //     },
  //     tomograms: [
  //       { tomogramId: 'tomo_001', status: 'accepted' },
  //       { tomogramId: 'tomo_002', status: 'rejected' },
  //       { tomogramId: 'tomo_003', status: 'uncertain' },
  //       { tomogramId: 'tomo_004', status: 'pending' },
  //       { tomogramId: 'tomo_005', status: 'pending' },
  //       { tomogramId: 'tomo_006', status: 'accepted' },
  //       { tomogramId: 'tomo_007', status: 'uncertain' },
  //       { tomogramId: 'tomo_008', status: 'rejected' },
  //       { tomogramId: 'tomo_009', status: 'pending' },
  //       { tomogramId: 'tomo_010', status: 'accepted' },
  //       { tomogramId: 'tomo_011', status: 'pending' },
  //       { tomogramId: 'tomo_012', status: 'accepted' },
  //       { tomogramId: 'tomo_013', status: 'uncertain' },
  //       { tomogramId: 'tomo_014', status: 'rejected' },
  //       { tomogramId: 'tomo_015', status: 'pending' },
  //       { tomogramId: 'tomo_016', status: 'accepted' },
  //     ],
  //   };
  // },
  [API.REVIEW_EXPORT]: {
    // This would typically return a file download
    // Mock just indicates success
    ok: true,
    exportPath: '/mnt/data/reviews/rev_abcdef123456/review_export.json',
  },
  [API.REVIEW_TOMOGRAMS]: [
    { tomogramId: 'tomo_001', status: 'accepted' },
    { tomogramId: 'tomo_002', status: 'rejected' },
    { tomogramId: 'tomo_003', status: 'uncertain' },
    { tomogramId: 'tomo_004', status: 'pending' },
    { tomogramId: 'tomo_005', status: 'pending' },
    // Additional tomograms would be listed here...
  ],
  // [API.TOMOGRAM_DETAIL]: (url: string) => {
  //   const tomogramId = url.split('/').pop();
  //   const details = {
  //     tomo_001: {
  //       tomogramId: 'tomo_001',
  //       displayName: 'Grid6_Tomo001',
  //       zarrPath: 'https://czii-onsite.czbiohub.org/krios1.processing/denoise/25apr21a/run001/Position_6_Vol.zarr',
  //       existingReview: {
  //         quality: 'accepted',
  //         rejectionReasons: [''],
  //         objectLabels: ['mitochondria', 'nucleus', 'ribosome', 'vesicle'],
  //       },
  //     },
  //     tomo_002: {
  //       tomogramId: 'tomo_002',
  //       displayName: 'Grid6_Tomo002',
  //       zarrPath: 'https://onsite.czbiohub.org/group.czii/ashley.anderson/hitl-samples/Position_6_Vol_rechunked.zarr/',
  //       existingReview: {
  //         quality: 'rejected',
  //         rejectionReasons: ['no features of interest', 'blurry'],
  //         objectLabels: ['tight junction', 'desmosome', 'gap junction', 'synapse', 'axon', 'dendrite', 'myelin sheath'],
  //       },
  //     },
  //     tomo_003: {
  //       tomogramId: 'tomo_003',
  //       displayName: 'Grid6_Tomo003',
  //       zarrPath: 'https://czii-onsite.czbiohub.org/krios1.processing/denoise/25apr21a/run001/Position_13_Vol.zarr/',
  //       existingReview: {
  //         quality: 'uncertain',
  //         objectLabels: [
  //           'lysosomal membrane',
  //           'ribosomal subunit',
  //           'proteasome',
  //           'spliceosome',
  //           'cytosolic protein complex',
  //           'signalosome',
  //           'transcription factor complex',
  //           'kinetochore',
  //           'telomere',
  //           'centromere',
  //         ],
  //       },
  //     },
  //     tomo_004: {
  //       tomogramId: 'tomo_004',
  //       displayName: 'Grid6_Tomo004',
  //       zarrPath: 'https://czii-onsite.czbiohub.org/krios1.processing/denoise/25apr21a/run001/Position_13_Vol.zarr/',
  //       existingReview: {
  //         quality: 'pending',
  //         objectLabels: [
  //           'lysosomal membrane',
  //           'ribosomal subunit',
  //           'proteasome',
  //           'spliceosome',
  //           'cytosolic protein complex',
  //           'signalosome',
  //           'transcription factor complex',
  //           'kinetochore',
  //           'telomere',
  //           'centromere',
  //         ],
  //       },
  //     },
  //   };
  //   return details[tomogramId as keyof typeof details] || null;
  // },
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const MOCKED_POST_APIS: Partial<Record<POST_API, any>> = {
  // [POST_API.CREATE_REVIEW]: {
  //   reviewId: '5570b672-ab28-4998-aa0e-0846d5c35964',
  //   sessionId: '24nov10',
  //   runId: 'run001',
  //   reconstructionType: 'Denoised',
  //   reviewName: 'Tomogram Quality - 24nov10 - run001 - denoised',
  //   totalCount: 100,
  //   status: 'not_started',
  //   createdAt: '2025-04-22T15:20:00Z',
  // },
  [POST_API.SAVE_REVIEW]: {
    ok: true,
    savedAt: '2025-04-22T16:42:10Z',
    savePath: '/mnt/data/reviews/rev_abcdef123456/review.json',
    reviewedCount: 75,
    totalCount: 100,
  },
  [POST_API.COMPLETE_REVIEW]: {
    ok: true,
    finishedAt: '2025-04-22T17:30:15Z',
    savePath: '/mnt/data/reviews/rev_abcdef123456/review.json',
  },
  // [POST_API.UPDATE_TOMOGRAM_REVIEW]: (options: { userIsOwner?: boolean } = {}) => {
  //   if (options.userIsOwner === false) {
  //     return {
  //       ok: false,
  //       error: 'You are not the owner of this review and cannot submit annotations.',
  //     };
  //   }
  //   return { ok: true };
  // },
};
