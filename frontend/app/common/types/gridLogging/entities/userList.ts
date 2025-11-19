export interface UserListResponse {
  total_users_count: number;
  users: UserList[];
}

export interface UserList {
  id: number;
  username: string;
  clean_username: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email: string;
}
