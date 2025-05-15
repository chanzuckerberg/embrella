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
  const [runOptions, setRunOptions] = useState<Array<AutocompleteOptionBasic>>([]);
  const [selectedRun, setSelectedRun] = useState<AutocompleteOptionBasic | undefined>(undefined);

  return (
    <div className="flex flex-col !p-[25px] relative gap-[40px]">
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
            onChange={(temSessionOption) => {
              setSelectedTemSession(temSessionOption);
              setReconstructionTypeOptions(
                temSessionOption?.session.runs
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
              onChange={(reconstructionTypeOption) => {
                setSelectedReconstructionType(reconstructionTypeOption);
                setRunOptions(
                  reconstructionTypeOption !== undefined
                    ? selectedTemSession.session.runs
                        .filter((run) => run.reconstructionTypes.includes(reconstructionTypeOption.name))
                        .map((run) => ({ name: run.runId }))
                    : []
                );
              }}
            />
          )}
          {selectedReconstructionType !== undefined && (
            <DropdownSelect
              topLabel="Run:"
              topLabelClass="!mt-[16px]"
              value={selectedRun}
              options={runOptions}
              onChange={(option) => {
                setSelectedRun(option);
              }}
            />
          )}
          {selectedRun !== undefined && (
            <>
              <div className="!mt-[16px] font-semibold">Selection details:</div>
              <div className="grid grid-rows-2 grid-cols-2 gap-[12px] !p-[16px] bg-[#f3f3f3]">
                <div>
                  <div className="font-semibold">Project:</div>
                  <div>{selectedTemSession?.session.projectName}</div>
                </div>
                <div>
                  <div className="font-semibold">Tomograms selected for review:</div>
                  <div>
                    {selectedTemSession?.session.runs
                      .filter((run) => run.reconstructionTypes.includes(selectedReconstructionType!.name))
                      .reduce((prevCount, runB) => prevCount + runB.numTomograms, 0)}
                  </div>
                </div>
                <div className="col-span-full">
                  <div className="font-semibold">Review results will be saved to:</div>
                  <div className="bg-[#dfdfdf] font-mono !px-[12px] !py-[4px]">
                    {selectedTemSession?.session.savePath}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
};
