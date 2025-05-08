'use client';

import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { TemSession } from '../ReviewsView/types';
import { API } from '@app/common/constants/api';
import { useMemo, useState } from 'react';
import { DropdownSelect } from '@app/common/components/DropdownSelect';
import { AutocompleteOptionBasic } from '@czi-sds/components';

interface TemSessionOption extends AutocompleteOptionBasic {
  session: TemSession;
}

export const CreateReviewView = () => {
  const temSessions = useFetchData<Array<TemSession>>(API.TEM_SESSIONS).data;
  const temSessionOptions = useMemo(
    () => temSessions?.map((session) => ({ name: session.sessionName, session })) ?? [],
    [temSessions]
  );
  const [selectedTemSession, setSelectedTemSession] = useState<TemSessionOption | undefined>(undefined);

  const [reconstructionTypeOptions, setReconstructionTypeOptions] = useState<Array<AutocompleteOptionBasic>>([]);
  const [selectedReconstructionType, setSelectedReconstructionType] = useState<AutocompleteOptionBasic | undefined>(
    undefined
  );

  return (
    <div className="flex flex-col !p-[25px] relative">
      <header className="text-[22px] font-semibold">Create New Review</header>
      <main className="flex justify-around">
        <div className="flex flex-col basis-[800px]">
          <header className="text-[18px] font-semibold">Select Data</header>
          <div className="text-[#6c6c6c] !mt-[4px]">Select data from Embrella to use in your review.</div>
          <DropdownSelect
            topLabel="TEM Session:"
            topLabelClass="!mt-[16px]"
            value={selectedTemSession}
            options={temSessionOptions}
            onChange={(option) => {
              setSelectedTemSession(option);
              setReconstructionTypeOptions(
                option?.session.runs
                  .flatMap((run) => run.reconstructionTypes)
                  .map((reconstructionType) => ({
                    name: reconstructionType,
                  })) ?? []
              );
            }}
            disabled={temSessions === undefined}
          />
          {selectedTemSession !== undefined && (
            <DropdownSelect
              topLabel="Reconstruction Type:"
              topLabelClass="!mt-[16px]"
              value={selectedReconstructionType}
              options={reconstructionTypeOptions}
              onChange={(option) => {
                setSelectedReconstructionType(option);
              }}
            />
          )}
        </div>
      </main>
    </div>
  );
};