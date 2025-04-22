export type API = GET_API | POST_API;

export enum GET_API {
  GRIDS = "/cryo_grids/v1/grids",
  GRIDS_FILTERS_LIST = "/cryo_grids/v1/filterlist",
  TOMOGRAMS = "/processes/v1/tomograms",
  TOMOGRAMS_FILTERLIST = "/processes/v1/filterlist",
  ANNOTATIONS = "/processes/v1/annotations",
  ANNOTATIONS_FILTERLIST = "/annotations/v1/filterlist",
  METADATA_SUMMARY = "/workflow/metadata/api/v1/summary",
  METADATA_VIZ = "/metadata/api/v1/data",

  // Mocked out:
  GET_REVIEWS = "/api/reviews",
  GET_SESSIONS = "/api/sessions",
  GET_SESSION = "/api/sessions/:sessionId",
  GET_REVIEW = "/api/reviews/:reviewId",
  SAVE_REVIEW = "/api/reviews/:reviewId/save",
  COMPLETE_REVIEW = "/api/reviews/:reviewId/complete",
  EXPORT_REVIEW = "/api/reviews/:reviewId/export",
  GET_REVIEW_TOMOGRAMS = "/api/reviews/:reviewId/tomograms",
  GET_REVIEW_TOMOGRAM = "/api/reviews/:reviewId/tomograms/:tomogramId",
}

export enum POST_API {
  CREATE_REVIEW = "/api/reviews",
  UPDATE_TOMOGRAM_REVIEW = "/api/reviews/:reviewId/tomograms/:tomogramId",
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const MOCKED_APIS: Partial<Record<API, Record<string, any>>> = {
  [GET_API.GET_REVIEWS]: [
    {
      reviewId: "rev_abcdef123456",
      reviewName: "Tomogram Quality - 24nov10 - run001 - denoised",
      reviewType: "tomogram_quality",
      sessionId: "24nov10",
      runId: "run001",
      updatedAt: "2025-04-08T15:20:00Z",
      status: "in_progress",
      reviewedCount: 75,
      totalCount: 100,
      reviewer: {
        id: "user_abc",
        name: "Yue Yu",
      },
    },
    {
      reviewId: "rev_456789abcdef",
      reviewName: "Tomogram Quality - 24oct30 - run001 - DCTF",
      reviewType: "tomogram_quality",
      sessionId: "24oct30",
      runId: "run001",
      updatedAt: "2025-04-01T10:15:00Z",
      status: "complete",
      reviewedCount: 84,
      totalCount: 84,
      reviewer: {
        id: "user_def",
        name: "Bryan Chu",
      },
    },
    {
      reviewId: "rev_fedcba654321",
      reviewName: "Tomogram Quality - Grid4_TestRun - run002 - Denoised",
      reviewType: "tomogram_quality",
      sessionId: "session_4321",
      runId: "run002",
      updatedAt: "2025-03-25T14:30:00Z",
      status: "not_started",
      reviewedCount: 0,
      totalCount: 20,
      reviewer: {
        id: "user_xyz",
        name: "John Doe",
      },
    },
  ],
  [GET_API.CREATE_REVIEW]: {
    reviewId: "rev_abcdef123456",
    sessionId: "24nov10",
    runId: "run001",
    reconstructionType: "Denoised",
    reviewName: "Tomogram Quality - 24nov10 - run001 - denoised",
    totalCount: 100,
    status: "not_started",
    createdAt: "2025-04-22T15:20:00Z",
  },
  [GET_API.GET_SESSIONS]: [
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
  [GET_API.GET_SESSION]: {
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
  [GET_API.GET_REVIEW]: {
    reviewId: "rev_abcdef123456",
    reviewName: "Tomogram Quality - 24nov10 - run001 - denoised",
    owner: {
      id: "user_abc",
      name: "Yue Yu",
    },
    tomograms: [
      { tomogramId: "tomo_001", status: "accepted" },
      { tomogramId: "tomo_002", status: "rejected" },
      { tomogramId: "tomo_003", status: "uncertain" },
      { tomogramId: "tomo_004", status: "pending" },
      // Additional tomograms would be listed here...
    ],
  },
  [GET_API.SAVE_REVIEW]: {
    ok: true,
    savedAt: "2025-04-22T16:42:10Z",
    savePath: "/mnt/data/reviews/rev_abcdef123456/review.json",
    reviewedCount: 75,
    totalCount: 100,
  },
  [GET_API.COMPLETE_REVIEW]: {
    ok: true,
    finishedAt: "2025-04-22T17:30:15Z",
    savePath: "/mnt/data/reviews/rev_abcdef123456/review.json",
  },
  [GET_API.EXPORT_REVIEW]: {
    // This would typically return a file download
    // Mock just indicates success
    ok: true,
    exportPath: "/mnt/data/reviews/rev_abcdef123456/review_export.json",
  },
  [GET_API.GET_REVIEW_TOMOGRAMS]: [
    { tomogramId: "tomo_001", status: "accepted" },
    { tomogramId: "tomo_002", status: "rejected" },
    { tomogramId: "tomo_003", status: "uncertain" },
    { tomogramId: "tomo_004", status: "pending" },
    { tomogramId: "tomo_005", status: "pending" },
    // Additional tomograms would be listed here...
  ],
  [GET_API.GET_REVIEW_TOMOGRAM]: {
    tomogramId: "tomo_002",
    displayName: "Grid6_Tomo002",
    zarrPath:
      "https://review-static.czbiohub.org/zarrs/Grid6_2025-04-22/Tomo_002.zarr",
    existingReview: {
      quality: "rejected",
      rejectionReasons: ["ice contamination", "low contrast"],
    },
  },
  [GET_API.UPDATE_TOMOGRAM_REVIEW]: {
    ok: true,
  },
};
