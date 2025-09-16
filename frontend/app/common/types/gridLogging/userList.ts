export interface userListResponse {
  total_users_count: number;
  users: UsersList[];
}

export interface UsersList {
  id: number;
  username: string;
  clean_username: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email: string;
}
