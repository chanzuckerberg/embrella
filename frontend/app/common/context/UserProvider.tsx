'use client';

import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { createContext, PropsWithChildren } from 'react';
import { API } from '../constants/api';

export interface User {
  id: number;
  username: string;
}

export const UserContext = createContext<User | undefined>(undefined);

export const UserProvider = ({ children }: PropsWithChildren) => {
  const user = useFetchData<User>(API.USER).data;
  return <UserContext.Provider value={user}>{children}</UserContext.Provider>;
};
