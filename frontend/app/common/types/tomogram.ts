import { MSISession } from "./msiSession";

export interface TomogramData {
  tomograms: {
    id: number;
    name: string;
    url: string;
  };
  procPlan: {
    id: number;
    name: string;
    url: string;
  };
  procRun: {
    id: number;
    notes: string;
    createdAt: string;
  };
  json: null;
  grid: {
    id: number;
    name: string;
    trashed: boolean;
    url: string;
    createdAt: string;
  };
  project: {
    id: number;
    name: string;
    url: string;
  };
  user: {
    id: number;
    name: string;
  };
  msiSession: MSISession;
}
