export interface FreezingSession {
    id: number;
    datetime: string;
    user: number;
    user_name: string;
    device: number;
    device_name: string;
    device_temperature: number;
    humidity: number;
    notes_page: number | null;
    display_name: string;
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