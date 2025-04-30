import { SearchParamValue } from "../types/search";

export enum API {
  USER = "/user",
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
  [API.REVIEWS]: (url: string) => {
    let reviews = [
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
        reviewedCount: 45,
        totalCount: 100,
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
          id: 1,
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
      {
        review: {
          id: 890123,
          name: "Tomogram Quality - 24dec15 - run001 - SART",
          url: "/api/reviews/rev_89012345mnop",
          type: "tomogram_quality",
        },
        session: {
          id: 24215,
          name: "Grid7_2025-04-10",
          url: "/api/sessions/24dec15",
        },
        runId: "run001",
        updatedAt: "2025-04-10T14:30:00Z",
        status: "complete",
        reviewedCount: 65,
        totalCount: 65,
        reviewer: {
          id: 104,
          name: "Emma Wilson",
          url: "/api/users/104",
        },
      },
      {
        review: {
          id: 901234,
          name: "Segmentation Labeling - Grid7_2025-04-10 - run002",
          url: "/api/reviews/rev_90123456qrst",
          type: "segmentation_labeling",
        },
        session: {
          id: 24215,
          name: "Grid7_2025-04-10",
          url: "/api/sessions/24dec15",
        },
        runId: "run002",
        updatedAt: "2025-04-12T09:45:00Z",
        status: "in_progress",
        reviewedCount: 42,
        totalCount: 70,
        reviewer: {
          id: 105,
          name: "Michael Chen",
          url: "/api/users/105",
        },
      },
      {
        review: {
          id: 112233,
          name: "Particle Picking - Grid5_2025-04-08 - run001",
          url: "/api/reviews/rev_112233uvwx",
          type: "particle_picking",
        },
        session: {
          id: 24030,
          name: "Grid5_2025-04-08",
          url: "/api/sessions/24oct30",
        },
        runId: "run001",
        updatedAt: "2025-04-20T16:20:00Z",
        status: "not_started",
        reviewedCount: 0,
        totalCount: 50,
        reviewer: {
          id: 106,
          name: "Sarah Johnson",
          url: "/api/users/106",
        },
      },
      {
        review: {
          id: 445566,
          name: "Tomogram Quality - 25jan05 - run001 - Denoised",
          url: "/api/reviews/rev_445566yzab",
          type: "tomogram_quality",
        },
        session: {
          id: 25005,
          name: "Grid8_2025-01-05",
          url: "/api/sessions/25jan05",
        },
        runId: "run001",
        updatedAt: "2025-01-06T11:10:00Z",
        status: "in_progress",
        reviewedCount: 120,
        totalCount: 120,
        reviewer: {
          id: 1,
          name: "Bryan Chu",
          url: "/api/users/102",
        },
      },
      {
        review: {
          id: 778899,
          name: "Tomogram Quality - 25feb20 - run003 - DCTF",
          url: "/api/reviews/rev_778899cdef",
          type: "tomogram_quality",
        },
        session: {
          id: 25220,
          name: "Grid9_2025-02-20",
          url: "/api/sessions/25feb20",
        },
        runId: "run003",
        updatedAt: "2025-02-22T08:30:00Z",
        status: "in_progress",
        reviewedCount: 48,
        totalCount: 95,
        reviewer: {
          id: 107,
          name: "Alex Roberts",
          url: "/api/users/107",
        },
      },
      {
        review: {
          id: 224466,
          name: "Particle Picking - Grid9_2025-02-20 - run002",
          url: "/api/reviews/rev_224466ghij",
          type: "particle_picking",
        },
        session: {
          id: 25220,
          name: "Grid9_2025-02-20",
          url: "/api/sessions/25feb20",
        },
        runId: "run002",
        updatedAt: "2025-03-01T14:15:00Z",
        status: "complete",
        reviewedCount: 80,
        totalCount: 80,
        reviewer: {
          id: 103,
          name: "John Doe",
          url: "/api/users/103",
        },
      },
      {
        review: {
          id: 335577,
          name: "Segmentation Labeling - 25mar15 - run001",
          url: "/api/reviews/rev_335577klmn",
          type: "segmentation_labeling",
        },
        session: {
          id: 25315,
          name: "Grid10_2025-03-15",
          url: "/api/sessions/25mar15",
        },
        runId: "run001",
        updatedAt: "2025-03-18T10:45:00Z",
        status: "not_started",
        reviewedCount: 0,
        totalCount: 110,
        reviewer: {
          id: 108,
          name: "Jessica Kim",
          url: "/api/users/108",
        },
      },
      {
        review: {
          id: 998877,
          name: "Tomogram Quality - 25apr01 - run001 - SART",
          url: "/api/reviews/rev_998877opqr",
          type: "tomogram_quality",
        },
        session: {
          id: 25401,
          name: "Grid11_2025-04-01",
          url: "/api/sessions/25apr01",
        },
        runId: "run001",
        updatedAt: "2025-04-05T09:20:00Z",
        status: "in_progress",
        reviewedCount: 25,
        totalCount: 75,
        reviewer: {
          id: 101,
          name: "Yue Yu",
          url: "/api/users/101",
        },
      },
    ];

    let params: SearchParamValue[] = [];
    try {
      params = JSON.parse(decodeURIComponent(url.split("q=")[1]));
      const searchParam = params.find((param) => param.category === "search");
      const pageParam = params.find((param) => param.category);
      if (searchParam !== undefined) {
        reviews = reviews.filter((review) =>
          review.review.name.includes(searchParam.value as string),
        );
      } else if (pageParam !== undefined) {
        reviews = reviews.slice(0, 10);
      }
    } catch (e) {
      console.log(e);
      console.log(`Mock function failed to parse ${url}`);
    }

    return {
      result: reviews,
      pagination: {
        page: 1,
        pageSize: 10,
        totalPages: 2,
        totalResults: 12,
      },
      sortBy: {
        sort: "updatedAt",
        asc: false,
      },
    };
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
