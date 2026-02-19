export interface FreezingSession {
  id: number;
  datetime: string;
  user: number;
  user_name: string;
  device: number;
  device_name: string;
  device_temperature: number;
  humidity: number;
  documentation_page: number | null;
  display_name: string;
}

export interface FreezingSessionDetail {
  id: number;
  name: string;
  datetime: string;
  user: string;
  device: string | null;
  temperature: number | null;
  humidity: number | null;
}

// Create request/response
export interface CreateFreezingSessionData {
  user: number;
  device: number;
  device_temperature: number;
  humidity: number;
  documentation_page?: number | null;
  freezingSessionDate?: Date | null;
}

export interface FreezingSessionCreateResponse {
  id: number;
  datetime: string;
  user: number;
  device: number;
  device_temperature: number;
  humidity: number;
  documentation_page: number | null;
  display_name: string;
}

// Form data (UI)
export interface FreezingSessionFormData {
  user: string;
  device: string;
  temperature: string;
  humidity: string;
  notesPage: string;
  freezingSessionDate: Date | null;
}

export interface FreezingSessionListResponse {
  total_freezing_sessions_count: number;
  results?: FreezingSession[];
  freezing_sessions?: FreezingSession[];
}

export const transformFreezingSession = (session: FreezingSession) => {
  return {
    ...session,
    label: session.display_name,
    value: session.id,
  };
};
