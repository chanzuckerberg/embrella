'use client';

import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { ReviewData, TemSession } from '../ReviewsView/types';
import { API, DJANGO_URL, POST_API } from '@app/common/constants/api';
import { useMemo, useRef, useState } from 'react';
import { DropdownSelect } from '@app/common/components/DropdownSelect';
import {
  AutocompleteOptionBasic,
  Button,
  DropdownMenu,
  Icon,
  InputSearch,
  InputText,
  TagFilter,
} from '@czi-sds/components';
import { fetchResource, postResource } from '@app/common/queries/fetchResource';
import { getRequestURL } from '@app/common/queries/utils';
import { useRouter } from 'next/navigation';

export const AVAILABLE_ANNOTATION_OBJECTS = [
  'carbon edge',
  'lysosome',
  'membrane protein complex',
  'ribosome',
  'vesicle',
  'cilium',
  'cytosolic ribosome',
  'mitochondrion',
  'endoplasmic reticulum',
  'golgi apparatus',
  'nucleus',
  'peroxisome',
  'chloroplast',
  'flagellum',
  'microtubule',
  'actin filament',
  'centrosome',
  'extracellular matrix',
  'plasma membrane',
  'nucleolus',
  'chromatin',
  'nuclear pore complex',
  'cytoplasmic inclusion',
  'lipid droplet',
  'vacuole',
  'cell wall',
  'tight junction',
  'desmosome',
  'gap junction',
  'synapse',
  'axon',
  'dendrite',
  'myelin sheath',
  'sarcomere',
  'basal body',
  'tonoplast',
  'phagosome',
  'autophagosome',
  'endosome',
  'lysosomal membrane',
  'ribosomal subunit',
  'proteasome',
  'spliceosome',
  'cytosolic protein complex',
  'signalosome',
  'transcription factor complex',
  'kinetochore',
  'telomere',
  'centromere',
  'nuclear envelope',
  'cytoskeletal element',
];

interface TemSessionOption extends AutocompleteOptionBasic {
  session: TemSession;
}

export const CreateReviewView = () => {
  const router = useRouter();

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

  const annotationObjectSettingsContainerRef = useRef<HTMLDivElement | null>(null);

  const annotationObjectSearchRef = useRef<HTMLDivElement | null>(null);
  const [annotationObjectValue, setAnnotationObjectValue] = useState('');
  const [selectedAnnotationObjects, setSelectedAnnotationObjects] = useState<Array<string>>([]);
  const [isAnnotationObjectsDropdownOpen, setIsAnnotationObjectsDropdownOpen] = useState(false);

  const previousSessionsButtonRef = useRef<HTMLButtonElement | null>(null);
  const previousSessionsRequestMade = useRef(false);
  const [previousSessions, setPreviousSessions] = useState<Array<ReviewData> | undefined>(undefined);
  const [isPreviousSessionsDropdownOpen, setIsPreviousSessionDropdownOpen] = useState(false);

  const [reviewName, setReviewName] = useState('');

  const [isCreatingReview, setIsCreatingReview] = useState(false);

  // #region JSX
  return (
    <div className="flex flex-col !p-[25px] relative gap-[40px]">
      <header className="text-[22px] font-semibold">Create New Review</header>
      <main className="self-center flex flex-col w-full max-w-[800px]">
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
              [...new Set(temSessionOption?.session.runs.map((runCount) => runCount.reconstructionType))].map(
                (reconstructionType) => ({
                  name: reconstructionType,
                })
              ) ?? []
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
                      .filter((run) => run.reconstructionType === reconstructionTypeOption.name)
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
              setReviewName(
                `Tomogram Quality - ${selectedTemSession?.name} - ${option?.name} - ${selectedReconstructionType.name}`
              );
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
                    .filter((run) => run.reconstructionType.includes(selectedReconstructionType!.name))
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
            <header className="text-[18px] font-semibold !mt-[24px]">Review Settings</header>
            <div className="text-[16px] !mt-[16px]">
              <span className="font-semibold">Review Type:</span> Tomogram Quality
            </div>
            <div className="text-[#6c6c6c] !mt-[4px]">
              Reviewer will provide inputs the overall quality of tomograms in the selected session. Additionally, they
              can provide optional labels depending on quality rating.
            </div>
            <div className="flex flex-col gap-[12px] !mt-[6px] !p-[16px] bg-[#f3f3f3] divide-y divide-[#c6c6c6]">
              <div className="grid grid-rows-2 grid-cols-[115px_1fr] gap-[6px] !pb-[12px]">
                <div className="font-semibold text-[14px]">Review input:</div>
                <div className="text-[14px]">Assign Whole-tomogram quality</div>
                <div className="font-semibold text-[12px]">Accepted values:</div>
                <div className="text-[#6c6c6c] text-[12px]">Accept, Reject, Uncertain</div>
              </div>
              <div
                className="grid grid-rows-2 grid-cols-[115px_1fr] gap-[6px] !pb-[12px]"
                ref={annotationObjectSettingsContainerRef}
              >
                <div className="font-semibold text-[14px]">Review input:</div>
                <div className="text-[14px]">Label Objects of Interest for Whole-tomogram (Optional)</div>
                <div className="font-semibold text-[12px]">Dependency:</div>
                <div className="text-[#6c6c6c] text-[12px]">Tomogram quality is set to &quot;Accept&quot;</div>
                <div className="font-semibold text-[12px]">Accepted values:</div>
                <div className="flex flex-col">
                  <div className="flex gap-[12px]">
                    {
                      // #region Annotation Objects
                    }
                    <InputSearch
                      id="annotationObjectsSearch"
                      label="Add Objects of Interest"
                      placeholder="Add Objects of Interest"
                      className="!m-0 bg-white basis-[400px]"
                      value={annotationObjectValue}
                      onChange={(event) => {
                        setAnnotationObjectValue(event.target.value);
                      }}
                      handleSubmit={(value: string) => {
                        setSelectedAnnotationObjects((prev) => {
                          const next = new Set(prev);
                          next.add(value);
                          return [...next];
                        });
                      }}
                      onClick={() => {
                        setIsAnnotationObjectsDropdownOpen(true);
                      }}
                      ref={annotationObjectSearchRef}
                    />
                    <DropdownMenu
                      multiple
                      freeSolo
                      options={AVAILABLE_ANNOTATION_OBJECTS.filter((object) =>
                        object.includes(annotationObjectValue.toLowerCase())
                      ).map((object) => ({ name: object }))}
                      open={isAnnotationObjectsDropdownOpen}
                      value={selectedAnnotationObjects}
                      // @ts-expect-error -- SDS type is not specific enough.
                      onChange={(_event: SyntheticEvent, selections: Array<AutocompleteOptionBasic | string>) => {
                        setSelectedAnnotationObjects(
                          // Free solo options are returned as just strings.
                          selections.map((selection) => (typeof selection === 'string' ? selection : selection.name))
                        );
                      }}
                      onClickAway={(event) => {
                        if (!annotationObjectSearchRef.current?.contains(event?.target as Node)) {
                          setIsAnnotationObjectsDropdownOpen(false);
                        }
                      }}
                      // @ts-expect-error -- Type is incorrect, value is a string.
                      isOptionEqualToValue={(option: AutocompleteOptionBasic, value: string) => {
                        return option.name === value;
                      }}
                      anchorEl={annotationObjectSearchRef.current}
                      width={annotationObjectSearchRef.current?.clientWidth}
                    />
                    {
                      // #region Previous Sessions
                    }
                    <Button
                      sdsStyle="square"
                      className="grow"
                      sdsType="secondary"
                      startIcon={<Icon sdsIcon="Plus" sdsSize="s" />}
                      endIcon={<Icon sdsIcon="ChevronDown" sdsSize="xs" />}
                      onClick={async () => {
                        setIsPreviousSessionDropdownOpen(true);
                        if (previousSessionsRequestMade.current === false) {
                          previousSessionsRequestMade.current = true;
                          const previousSessions =
                            (await (await fetchResource(getRequestURL(DJANGO_URL, API.REVIEWS))).json())?.result ?? [];
                          setPreviousSessions(previousSessions);
                        }
                      }}
                      ref={previousSessionsButtonRef}
                    >
                      Add from Previous Session
                    </Button>
                    <DropdownMenu
                      search
                      loading={previousSessions === undefined}
                      loadingText="Loading..."
                      options={
                        previousSessions?.map((review) => ({
                          name: review.review.name,
                          details: review.review.annotationObjects.join(', '),
                          annotationObjects: review.review.annotationObjects,
                        })) ?? []
                      }
                      open={isPreviousSessionsDropdownOpen}
                      // @ts-expect-error -- SDS type is not specific enough.
                      onChange={(_event: SyntheticEvent, selection: { annotationObjects: string[] }) => {
                        setSelectedAnnotationObjects((prev) => [...new Set([...prev, ...selection.annotationObjects])]);
                        setIsPreviousSessionDropdownOpen(false);
                      }}
                      onClickAway={() => {
                        setIsPreviousSessionDropdownOpen(false);
                      }}
                      anchorEl={previousSessionsButtonRef.current}
                      width={annotationObjectSettingsContainerRef.current?.clientWidth}
                    />
                  </div>
                  <div className="!mt-[8px] flex flex-wrap gap-[6px]">
                    {selectedAnnotationObjects.map((object: string) => (
                      <TagFilter
                        key={object}
                        label={object}
                        className="!m-0"
                        onDelete={() => {
                          const index = selectedAnnotationObjects.indexOf(object);
                          setSelectedAnnotationObjects((prev) => {
                            const next = [...prev];
                            next.splice(index, 1);
                            return next;
                          });
                        }}
                      />
                    ))}
                  </div>
                </div>
              </div>
              <div className="grid grid-rows-2 grid-cols-[115px_1fr] gap-[6px]">
                <div className="font-semibold text-[14px]">Review input:</div>
                <div className="text-[14px]">Label Rejection Reason (Optional)</div>
                <div className="font-semibold text-[12px]">Dependency:</div>
                <div className="text-[#6c6c6c] text-[12px]">Tomogram quality is set to &quot;Reject&quot;</div>
                <div className="font-semibold text-[12px]">Accepted values:</div>
                <div className="text-[#6c6c6c] text-[12px]">Bad tomogram quality, No features of interest</div>
              </div>
            </div>
            {
              // #region Name
            }
            <div className="!mt-[24px] font-semibold text-[18px]">Review Name</div>
            <div className="text-[13px] text-[#6c6c6c] !mt-[4px]">
              This name will be used to identify this review in a table or menu. You can update or modify the
              auto-generated name.
            </div>
            <InputText
              id="reviewName"
              value={reviewName}
              onChange={(event) => {
                setReviewName(event.target.value);
              }}
              variant="outlined"
              className="!mt-[2px] !mb-[24px]"
              label="reviewName"
              hideLabel
            />
            <Button
              onClick={async () => {
                setIsCreatingReview(true);
                const submitResponse = await postResource(getRequestURL(DJANGO_URL, POST_API.CREATE_REVIEW), {
                  reviewName,
                  reviewType: 'tomogram_quality',
                  sessionId: selectedTemSession!.session.id,
                  runId: selectedRun!.name,
                  reconstructionType: selectedReconstructionType!.name,
                  annotationObjects: selectedAnnotationObjects,
                });
                if (submitResponse.status === 200) {
                  router.push(`/reviews/${(await submitResponse.json()).reviewId}`);
                } else {
                  setIsCreatingReview(false);
                }
              }}
              endIcon={isCreatingReview && <Icon sdsIcon={'Loading'} sdsSize={'s'} />}
              disabled={isCreatingReview}
              sdsStyle="square"
              className="self-start"
            >
              Create Review
            </Button>
          </>
        )}
      </main>
    </div>
  );
};
