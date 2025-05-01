"use client";

import { useFetchData } from "@hooks/useFetchData/useFetchData";
import { TemSession } from "../ReviewsView/types";
import configs from "@configs/local";
import { API } from "@app/common/constants/api";
import { useMemo, useState } from "react";
import { DropdownSelect } from "@app/common/components/DropdownSelect";
import { AutocompleteOptionBasic } from "@czi-sds/components";

interface TemSessionOption extends AutocompleteOptionBasic {
  session: TemSession;
}

export const CreateReviewView = () => {
  const temSessions = useFetchData<Array<TemSession>>(
    configs.API_URL,
    API.TEM_SESSIONS,
  ).data;

  const temSessionOptions = useMemo(
    () =>
      temSessions?.map((session) => ({ name: session.sessionName, session })) ??
      [],
    [temSessions],
  );
  const [selectedTemSession, setSelectedTemSession] = useState<
    TemSessionOption | undefined
  >(undefined);
  const [reconstructionTypeOptions, setReconstructionTypeOptions] = useState<
    Array<AutocompleteOptionBasic>
  >([]);
  const [selectedReconstructionType, setSelectedReconstructionType] = useState<
    AutocompleteOptionBasic | undefined
  >(undefined);
  const [runOptions, setRunOptions] = useState<Array<AutocompleteOptionBasic>>(
    [],
  );
  const [selectedRun, setSelectedRun] = useState<
    AutocompleteOptionBasic | undefined
  >(undefined);

  return (
    <div className="flex flex-col !p-[25px] relative">
      <header className="text-[22px] font-semibold">Create New Review</header>
      <main className="flex justify-around">
        <div className="flex flex-col basis-[800px]">
          <header className="text-[18px] font-semibold">Select Data</header>
          <div className="text-[#6c6c6c] !mt-[4px]">
            Select data from Embrella to use in your review.
          </div>
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
                  })) ?? [],
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
                        .filter((run) =>
                          run.reconstructionTypes.includes(
                            reconstructionTypeOption.name,
                          ),
                        )
                        .map((run) => ({ name: run.runId }))
                    : [],
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
        </div>
      </main>
    </div>
  );
};
