import { GridData } from "@/common/types";

// TODO(cc) - temporary API response data.
export const GRIDS: GridData[] = [
  {
    grid: {
      id: 1,
      name: "grid1 (id=1)",
      trashed: false,
      url: "http://umbrella.czbiohub.org/admin/cryo_grids/cryogrid/1",
      createdAt: "2024-08-26",
    },
    cassette: {
      name: "C1",
    },
    project: {
      id: 1,
      name: "BD01",
      url: "http://umbrella.czbiohub.org/admin/projects/project/1",
    },
    puck: {
      name: "puck1",
    },
    user: {
      id: 1,
      name: "test",
    },
    freezingPlan: {
      id: 1,
      sample: [
        {
          id: 1,
          name: "lysosome without tag",
          url: "http://umbrella.czbiohub.org/admin/samples/1",
        },
        {
          id: 2,
          name: "lysosome without tag X",
          url: "http://umbrella.czbiohub.org/admin/samples/2",
        },
      ],
    },
    freezingSession: {
      id: 1,
      createdAt: "2024-08-27 05:13",
    },
    screeningSession: "24aug26a",
    msiSession: [
      {
        id: 1,
        name: "24aug26a",
        url: "http://umbrella.czbiohub.org/tem/1",
      },
    ],
  },
  {
    grid: {
      id: 2,
      name: "grid2 (id=2)",
      trashed: false,
      url: "http://umbrella.czbiohub.org/admin/cryo_grids/cryogrid/1",
      createdAt: "2024-08-26",
    },
    cassette: {
      name: "C1",
    },
    project: {
      id: 1,
      name: "BD02",
      url: "http://umbrella.czbiohub.org/admin/projects/project/1",
    },
    puck: {
      name: "puck1",
    },
    user: {
      id: 1,
      name: "test",
    },
    freezingPlan: {
      id: 1,
      sample: [
        {
          id: 1,
          name: "Xlysosome without tag",
          url: "http://umbrella.czbiohub.org/admin/samples/1",
        },
      ],
    },
    freezingSession: {
      id: 1,
      createdAt: "2024-08-27 05:13",
    },
    screeningSession: "24aug26a",
    msiSession: [
      {
        id: 1,
        name: "24aug26a",
        url: "http://umbrella.czbiohub.org/tem/1",
      },
    ],
  },
];
