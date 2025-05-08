'use client';

import { DropdownMenu, InputDropdown } from '@czi-sds/components';
import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { TemSession } from '../ReviewsView/types';
import { API } from '@app/common/constants/api';
import { useMemo, useRef, useState } from 'react';

export const CreateReviewView = () => {
  const temSessionInputRef = useRef<HTMLElement | null>(null);
  const temSessions = useFetchData<Array<TemSession>>(API.TEM_SESSIONS).data;
  const temSessionOptions = useMemo(
    () => temSessions?.map((session) => ({ name: session.sessionName })) ?? [],
    [temSessions]
  );
  const [isTemSessionDropdownOpen, setIsTemSessionDropdownOpen] = useState(false);

  return (
    <div className="flex flex-col !p-[25px] relative">
      <header className="text-[22px] font-semibold">Create New Review</header>
      <main className="flex justify-around">
        <div className="flex flex-col basis-[800px]">
          <header className="text-[18px] font-semibold">Select Data</header>
          <div className="text-[#6c6c6c] !mt-[4px]">Select data from Embrella to use in your review.</div>
          <div className="font-semibold !mt-[16px]">TEM Session:</div>
          <InputDropdown
            label="Select"
            onClick={(e) => {
              temSessionInputRef.current = e.currentTarget;
              setIsTemSessionDropdownOpen((prev) => !prev);
            }}
          />
          <DropdownMenu
            search
            options={temSessionOptions}
            open={isTemSessionDropdownOpen}
            onClickAway={() => {
              setIsTemSessionDropdownOpen(false);
            }}
            anchorEl={temSessionInputRef.current}
            width={temSessionInputRef.current?.clientWidth}
          />
        </div>
      </main>
    </div>
  );
};
