export enum API {
  GRIDS = "/cryo_grids/v1/grids",
  GRIDS_FILTERS_LIST = "/cryo_grids/v1/filterlist",
  TOMOGRAMS = "/processes/v1/tomograms",
  TOMOGRAMS_FILTERLIST = "/processes/v1/filterlist",
  ANNOTATIONS = "/processes/v1/annotations",
  ANNOTATIONS_FILTERLIST = "/annotations/v1/filterlist",
  METADATA_SUMMARY = "/workflow/metadata/api/v1/summary",
  METADATA_VIZ = "/workflow/metadata/api/v1/data",

  // Mocked out:
  REVIEWS = "/api/reviews",
  TEM_SESSIONS = "/api/sessions",
  TEM_SESSION = "/api/sessions/:sessionId",
  REVIEW = "/api/reviews/:reviewId",
  REVIEW_EXPORT = "/api/reviews/:reviewId/export",
  REVIEW_TOMOGRAMS = "/api/reviews/:reviewId/tomograms",
  REVIEW_TOMOGRAM = "/api/reviews/:reviewId/tomograms/:tomogramId",
}

export enum POST_API {
  CREATE_REVIEW = "/api/reviews",
  SAVE_REVIEW = "/api/reviews/:reviewId/save",
  COMPLETE_REVIEW = "/api/reviews/:reviewId/complete",
  UPDATE_TOMOGRAM_REVIEW = "/api/reviews/:reviewId/tomograms/:tomogramId",
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const MOCKED_APIS: Partial<Record<API, any>> = {
  [API.REVIEWS]: {
    result: [
      {
        review: {
          id: 123456,
          name: "Tomogram Quality - 24nov10 - run001 - denoised",
          url: "/api/reviews/rev_abcdef123456",
          type: "tomogram_quality",
        },
        session: {
          id: 24110,
          name: "Grid6_2025-04-22",
          url: "/api/sessions/24nov10",
        },
        updatedAt: "2025-04-22T15:20:00Z",
        status: "in_progress",
        reviewer: {
          id: 101,
          name: "Yue Yu",
          url: "/api/users/101",
        },
      },
      {
        review: {
          id: 456789,
          name: "Tomogram Quality - 24oct30 - run001 - DCTF",
          url: "/api/reviews/rev_456789abcdef",
          type: "tomogram_quality",
        },
        session: {
          id: 24030,
          name: "Grid5_2025-04-08",
          url: "/api/sessions/24oct30",
        },
        runId: "run001",
        updatedAt: "2025-04-18T10:15:00Z",
        status: "complete",
        reviewedCount: 84,
        totalCount: 84,
        reviewer: {
          id: 102,
          name: "Bryan Chu",
          url: "/api/users/102",
        },
      },
      {
        review: {
          id: 654321,
          name: "Tomogram Quality - Grid4_TestRun - run002 - Denoised",
          url: "/api/reviews/rev_fedcba654321",
          type: "tomogram_quality",
        },
        session: {
          id: 4321,
          name: "Grid4_TestRun",
          url: "/api/sessions/session_4321",
        },
        runId: "run002",
        updatedAt: "2025-04-15T14:30:00Z",
        status: "not_started",
        reviewedCount: 0,
        totalCount: 20,
        reviewer: {
          id: 103,
          name: "John Doe",
          url: "/api/users/103",
        },
      },
      {
        review: {
          id: 789012,
          name: "Segmentation Labeling - 24nov10 - run001",
          url: "/api/reviews/rev_789012ghijkl",
          type: "segmentation_labeling",
        },
        session: {
          id: 24110,
          name: "Grid6_2025-04-22",
          url: "/api/sessions/24nov10",
        },
        runId: "run001",
        updatedAt: "2025-04-21T11:45:00Z",
        status: "in_progress",
        reviewedCount: 30,
        totalCount: 100,
        reviewer: {
          id: 101,
          name: "Yue Yu",
          url: "/api/users/101",
        },
      },
    ],
    pagination: {
      page: 1,
      pageSize: 10,
      totalPages: 1,
      totalResults: 4,
    },
    sortBy: {
      sort: "updatedAt",
      asc: false,
    },
  },
  [API.TEM_SESSIONS]: [
    {
      sessionId: "24oct30",
      sessionName: "Grid5_2025-04-08",
      createdAt: "2025-04-08T13:22:00Z",
      runs: [
        {
          runId: "run001",
          numTomograms: 84,
          reconstructionTypes: ["DCTF", "Denoised", "SART"],
        },
      ],
    },
    {
      sessionId: "24nov10",
      sessionName: "Grid6_2025-04-22",
      createdAt: "2025-04-22T09:10:00Z",
      runs: [
        {
          runId: "run001",
          numTomograms: 100,
          reconstructionTypes: ["DCTF", "Denoised", "SART"],
        },
      ],
    },
    {
      sessionId: "session_4321",
      sessionName: "Grid4_TestRun",
      createdAt: "2025-04-01T09:10:00Z",
      runs: [
        {
          runId: "run001",
          numTomograms: 20,
          reconstructionTypes: ["DCTF", "SART"],
        },
        {
          runId: "run002",
          numTomograms: 20,
          reconstructionTypes: ["Denoised"],
        },
      ],
    },
  ],
  [API.TEM_SESSION]: {
    sessionId: "24nov10",
    sessionName: "Grid6_2025-04-22",
    createdAt: "2025-04-22T09:10:00Z",
    savePath: "/mnt/data/tomograms/2025-04-22/Grid6",
    metadata: {
      microscope: "Titan Krios",
      operator: "Yue Yu",
      project: "SARS-CoV-2",
    },
    runs: [
      {
        runId: "run001",
        numTomograms: 100,
        reconstructionTypes: ["DCTF", "Denoised", "SART"],
      },
    ],
  },
  [API.REVIEW]: {
    reviewId: "rev_abcdef123456",
    reviewName: "Tomogram Quality - 24nov10 - run001 - denoised",
    owner: {
      id: 101,
      name: "Yue Yu",
      url: "/api/users/101",
    },
    tomograms: [
      { tomogramId: "tomo_001", status: "accepted" },
      { tomogramId: "tomo_003", status: "uncertain" },
      { tomogramId: "tomo_004", status: "pending" },
      // Additional tomograms would be listed here...
    ],
  },
  [API.REVIEW_EXPORT]: {
    // This would typically return a file download
    // Mock just indicates success
    ok: true,
    exportPath: "/mnt/data/reviews/rev_abcdef123456/review_export.json",
  },
  [API.REVIEW_TOMOGRAMS]: [
    { tomogramId: "tomo_001", status: "accepted" },
    { tomogramId: "tomo_002", status: "rejected" },
    { tomogramId: "tomo_003", status: "uncertain" },
    { tomogramId: "tomo_004", status: "pending" },
    { tomogramId: "tomo_005", status: "pending" },
    // Additional tomograms would be listed here...
  ],
  [API.REVIEW_TOMOGRAM]: {
    tomogramId: "tomo_002",
    displayName: "Grid6_Tomo002",
    zarrPath:
      "https://review-static.czbiohub.org/zarrs/Grid6_2025-04-22/Tomo_002.zarr",
    existingReview: {
      quality: "rejected",
      rejectionReasons: ["ice contamination", "low contrast"],
    },
  },
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const MOCKED_POST_APIS: Partial<Record<POST_API, any>> = {
  [POST_API.CREATE_REVIEW]: {
    reviewId: "rev_abcdef123456",
    sessionId: "24nov10",
    runId: "run001",
    reconstructionType: "Denoised",
    reviewName: "Tomogram Quality - 24nov10 - run001 - denoised",
    totalCount: 100,
    status: "not_started",
    createdAt: "2025-04-22T15:20:00Z",
  },
  [POST_API.SAVE_REVIEW]: {
    ok: true,
    savedAt: "2025-04-22T16:42:10Z",
    savePath: "/mnt/data/reviews/rev_abcdef123456/review.json",
    reviewedCount: 75,
    totalCount: 100,
  },
  [POST_API.COMPLETE_REVIEW]: {
    ok: true,
    finishedAt: "2025-04-22T17:30:15Z",
    savePath: "/mnt/data/reviews/rev_abcdef123456/review.json",
  },
  [POST_API.UPDATE_TOMOGRAM_REVIEW]: {
    ok: true,
  },
};
