import { MSISession } from "./msiSession";

export interface TomogramData {
  // TODO: should this be singular?
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
    note: string;
  };
  json: null;
  grid: {
    id: number;
    name: string;
    trashed: boolean;
    url: string;
    createdAt: string;
  };
  // TODO: should this be singular?
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
