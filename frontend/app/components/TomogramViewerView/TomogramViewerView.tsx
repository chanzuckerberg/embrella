'use client';

import { useState, useEffect, useCallback, useReducer, useContext, useRef } from 'react';
import { TopBar } from './components/TopBar';
import { SideBar } from './components/SideBar';
import { Review, ReviewTomogramDetail } from './types';
import { QualityControls } from './components/QualityControls';
import { OmeZarrImageViewer } from '../../../imaging-active-learning/packages/react/src/components/viewers/OmeZarrImageViewer';
import { Region } from '../../../imaging-active-learning/packages/core/src/data/region';
import { useHotkeys } from 'react-hotkeys-hook';
import { getRegionFromZattrs } from './utils';
import { useIdetik } from '../../../imaging-active-learning/packages/react/src/components/hooks';
import { API, MOCKED_APIS, POST_API, MOCKED_POST_APIS } from '../../../app/common/constants/api';
import { RejectionReasonsSelector } from './components/RejectionReasonsSelector';
import { ObjectLabelsSelector } from './components/ObjectLabelsSelector';
import { AVAILABLE_ANNOTATION_OBJECTS } from '../CreateReviewView/CreateReviewView';
import { Button, Icon } from '@czi-sds/components';
import { UserContext } from '@app/common/context/UserProvider';
import { PermissionBanner } from './components/PermissionBanner';
import { debounce } from '@mui/material';
import { DJANGO_URL } from '../../../app/common/constants/api';

interface TomogramViewerProps {
  review: Review;
}

interface TomogramState {
  selectedTomogram: string | undefined;
  tomogramDetail: ReviewTomogramDetail | null;
  contrastLimits: [number, number];
  selectedRejectionReasons: string[];
  selectedQuality: 'accepted' | 'rejected' | 'uncertain' | 'exemplary' | 'pending';
  selectedObjectLabels: string[];
  saveState?: 'saving' | 'saved' | 'failed';
}

type TomogramAction =
  | { type: 'SET_SELECTED_TOMOGRAM'; payload: string }
  | { type: 'SET_TOMOGRAM_DETAIL'; payload: ReviewTomogramDetail | null }
  | { type: 'SET_CONTRAST_LIMITS'; payload: [number, number] }
  | { type: 'SET_REJECTION_REASONS'; payload: string[] }
  | { type: 'SET_QUALITY'; payload: 'accepted' | 'rejected' | 'uncertain' | 'exemplary' | 'pending' }
  | { type: 'SET_OBJECT_LABELS'; payload: string[] }
  | { type: 'RESET_REVIEW_STATE' }
  | { type: 'SET_SAVE_STATE'; payload: 'saving' | 'saved' | 'failed' | undefined };

const initialState: TomogramState = {
  selectedTomogram: undefined,
  tomogramDetail: null,
  contrastLimits: [-0.00001, 0.00001],
  selectedRejectionReasons: [],
  selectedQuality: 'pending',
  selectedObjectLabels: [],
};

function tomogramReducer(state: TomogramState, action: TomogramAction): TomogramState {
  switch (action.type) {
    case 'SET_SELECTED_TOMOGRAM':
      return { ...state, selectedTomogram: action.payload };
    case 'SET_TOMOGRAM_DETAIL':
      return { ...state, tomogramDetail: action.payload };
    case 'SET_CONTRAST_LIMITS':
      return { ...state, contrastLimits: action.payload };
    case 'SET_REJECTION_REASONS':
      return { ...state, selectedRejectionReasons: action.payload };
    case 'SET_QUALITY':
      return { ...state, selectedQuality: action.payload };
    case 'SET_OBJECT_LABELS':
      return { ...state, selectedObjectLabels: action.payload };
    case 'RESET_REVIEW_STATE':
      return {
        ...state,
        selectedQuality: 'pending',
        selectedRejectionReasons: [],
        selectedObjectLabels: [],
      };
    case 'SET_SAVE_STATE':
      return { ...state, saveState: action.payload };
    default:
      return state;
  }
}

export const TomogramViewerView = ({ review }: TomogramViewerProps) => {
  const [state, dispatch] = useReducer(tomogramReducer, {
    ...initialState,
    selectedTomogram: review.tomograms[0]?.tomogramId,
  });
  const [region, setRegion] = useState<Region | null>(null);
  const lastAnswerUpdateTime = useRef<number | undefined>(undefined);

  const seriesDimensionName = 'z'; // TODO: get from zarr metadata
  const { imageSeriesLayer, channels } = useIdetik();
  const currentUser = useContext(UserContext);
  const userCanReview = currentUser?.id === review.owner.id;

  useHotkeys('a', () => {
    dispatchAndSave({ type: 'SET_QUALITY', payload: 'accepted' });
  });
  useHotkeys('r', () => {
    dispatchAndSave({ type: 'SET_QUALITY', payload: 'rejected' });
  });
  useHotkeys('u', () => {
    dispatchAndSave({ type: 'SET_QUALITY', payload: 'uncertain' });
  });
  useHotkeys('e', () => {
    dispatchAndSave({ type: 'SET_QUALITY', payload: 'exemplary' });
  });
  useHotkeys('left', () => {
    handlePrevious();
  });
  useHotkeys('right', () => {
    handleNext();
  });

  const handleContrastLimitsChange = useCallback(
    (newLimits: [number, number]) => {
      if (!imageSeriesLayer) return;

      const updatedChannels = channels.map((channel) => ({
        ...channel,
        contrastLimits: newLimits,
      }));
      dispatch({ type: 'SET_CONTRAST_LIMITS', payload: newLimits });
      imageSeriesLayer.setChannelProps(updatedChannels);
    },
    [imageSeriesLayer, channels]
  );

  useEffect(() => {
    const fetchRegion = async () => {
      if (!state.tomogramDetail?.zarrPath) return;
      const region = await getRegionFromZattrs(state.tomogramDetail.zarrPath);
      setRegion(region);
    };
    fetchRegion();
  }, [state.tomogramDetail?.zarrPath]);

  const currentIndex = state.selectedTomogram
    ? review.tomograms.findIndex((t) => t.tomogramId === state.selectedTomogram)
    : -1;

  const handlePrevious = () => {
    if (currentIndex > 0) {
      dispatch({
        type: 'SET_SELECTED_TOMOGRAM',
        payload: review.tomograms[currentIndex - 1].tomogramId,
      });
    }
  };

  const handleNext = () => {
    if (currentIndex < review.tomograms.length - 1) {
      dispatch({
        type: 'SET_SELECTED_TOMOGRAM',
        payload: review.tomograms[currentIndex + 1].tomogramId,
      });
    }
  };

  const getTomogramIdForStatus = (status: string | undefined) => {
    switch (status) {
      case 'accepted':
        return 'tomo_001';
      case 'rejected':
        return 'tomo_002';
      case 'uncertain':
        return 'tomo_003';
      case 'pending':
        return 'tomo_004';
      default:
        return 'tomo_001';
    }
  };

  const updateTomogramState = (tomogramDetail: ReviewTomogramDetail | null) => {
    if (tomogramDetail) {
      dispatch({ type: 'SET_TOMOGRAM_DETAIL', payload: tomogramDetail });
      dispatch({
        type: 'SET_OBJECT_LABELS',
        payload: tomogramDetail.existingReview?.objectLabels || [],
      });
      dispatch({
        type: 'SET_REJECTION_REASONS',
        payload: tomogramDetail.existingReview?.rejectionReasons || [],
      });
      dispatch({
        type: 'SET_QUALITY',
        payload: tomogramDetail.existingReview?.quality || 'pending',
      });
    } else {
      dispatch({ type: 'SET_TOMOGRAM_DETAIL', payload: null });
    }
  };

  useEffect(() => {
    async function fetchTomogramDetail() {
      if (!state.selectedTomogram) return;

      // Previous code (commented out just in case)
      // const selectedTomogramStatus = review.tomograms.find((t) => t.tomogramId === state.selectedTomogram)?.status;
      // const allowedTomograms = ['tomo_001', 'tomo_002', 'tomo_003', 'tomo_004'];
      // const tomogramIdToUse = allowedTomograms.includes(state.selectedTomogram)
      //   ? state.selectedTomogram
      //   : getTomogramIdForStatus(selectedTomogramStatus);
      // const url = `/api/reviews/${review.reviewId}/tomograms/${tomogramIdToUse}`;
      // const tomogramDetail = MOCKED_APIS[API.TOMOGRAM_DETAIL](url);

      try {
        const response = await fetch(`${DJANGO_URL}/api/reviews/${review.reviewId}/tomograms/${state.selectedTomogram}`);
        if (!response.ok) {
          throw new Error('Failed to fetch tomogram detail');
        }
        const tomogramDetail = await response.json();
        updateTomogramState(tomogramDetail);
      } catch (error) {
        console.error('Error fetching tomogram detail:', error);
        updateTomogramState(null);
      }
    }

    fetchTomogramDetail();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- Fetch whenever tomogram changes.
  }, [state.selectedTomogram]);

  const save = async () => {
    if (!state.selectedTomogram) return;
    dispatch({ type: 'SET_SAVE_STATE', payload: 'saving' });
    const now = Date.now();
    lastAnswerUpdateTime.current = now;

    // TODO: Real API.
    const saveResponse = await new Promise((resolve) =>
      setTimeout(() => {
        resolve(
          MOCKED_POST_APIS[POST_API.UPDATE_TOMOGRAM_REVIEW]({
            tomogramId: state.selectedTomogram,
            quality: state.selectedQuality,
            objectLabels: state.selectedObjectLabels,
            rejectionReasons: state.selectedRejectionReasons,
          })
        );
      }, 1000)
    );
    if (lastAnswerUpdateTime.current > now) {
      // A newer save request has been made.
      return;
    }
    if (saveResponse !== undefined) {
      dispatch({ type: 'SET_SAVE_STATE', payload: 'saved' });
    }
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps -- No dependencies, only preserves scope.
  const debouncedSave = useCallback(debounce(save, /* wait */ 2_000), []);

  const dispatchAndSave = (value: TomogramAction): void => {
    if (!userCanReview) return;
    dispatch(value);
    dispatch({ type: 'SET_SAVE_STATE', payload: undefined });
    debouncedSave();
  };

  return (
    <div className="w-full h-screen flex flex-col items-stretch">
      <TopBar saveState={state.saveState} />
      {!userCanReview && <PermissionBanner ownerName={review.owner.name} />}
      <div className="flex-auto flex border-t border-gray-300">
        <SideBar
          reviewName={review.reviewName}
          tomograms={review.tomograms}
          selectedTomogram={state.selectedTomogram}
          tomogramDetail={state.tomogramDetail}
          currentIndex={currentIndex}
          onPrevious={handlePrevious}
          onNext={handleNext}
          onSelectTomogram={(tomogramId) => dispatch({ type: 'SET_SELECTED_TOMOGRAM', payload: tomogramId })}
          contrastLimits={state.contrastLimits}
          onContrastLimitsChange={handleContrastLimitsChange}
        />
        <div className="flex-auto flex flex-col p-6 items-center justify-center border-x-[2px] border-gray-300 bg-gray-200">
          {state.tomogramDetail?.zarrPath !== undefined && !region && <div>Loading region...</div>}
          {state.tomogramDetail?.zarrPath !== undefined &&
            region &&
            !region.some((d) => d.dimension === seriesDimensionName) && (
              <div>Error: Region missing required dimension &quot;{seriesDimensionName}&quot;</div>
            )}
          {state.tomogramDetail?.zarrPath !== undefined &&
            region &&
            region.some((d) => d.dimension === seriesDimensionName) && (
              <OmeZarrImageViewer
                sourceUrl={state.tomogramDetail.zarrPath}
                region={region}
                seriesDimensionName={seriesDimensionName}
                allSlicesSizeEstimate="250 MB"
                fallbackContrastLimits={state.contrastLimits}
                resolutionLevel={2} // Set the desired resolution level (0 = highest res, 1 = lower res, etc.)
                shouldLoadMiddleZ={true}
                shouldAutoLoadAllSlices={true}
                classNames={{
                  root: 'bg-dark-sds-color-primitive-gray-100',
                }}
              />
            )}
        </div>
        <div className="flex flex-col gap-3">
          <div className="shrink-0 !pt-[20px] !pr-[20px] !pl-[20px] !pb-[20px]">
            <QualityControls
              isDisabled={!userCanReview}
              selectedQuality={state.selectedQuality}
              onAccept={() => {
                dispatchAndSave({ type: 'SET_QUALITY', payload: 'accepted' });
              }}
              onReject={() => {
                dispatchAndSave({ type: 'SET_QUALITY', payload: 'rejected' });
              }}
              onUncertain={() => {
                dispatchAndSave({ type: 'SET_QUALITY', payload: 'uncertain' });
              }}
              onExemplary={() => {
                dispatchAndSave({ type: 'SET_QUALITY', payload: 'exemplary' });
              }}
            />
          </div>
          {(state.selectedQuality === 'accepted' || state.selectedQuality === 'uncertain') && (
            <div className="shrink-0 !pb-[20px] !pr-[20px] !pl-[20px] !pt-0">
              <ObjectLabelsSelector
                isDisabled={!userCanReview}
                availableObjects={AVAILABLE_ANNOTATION_OBJECTS}
                selectedObjects={state.selectedObjectLabels}
                setSelectedObjects={(labels) => {
                  dispatchAndSave({ type: 'SET_OBJECT_LABELS', payload: labels });
                }}
              />
            </div>
          )}
          {state.selectedQuality === 'rejected' && (
            <div className="shrink-0 !pb-[20px] !pr-[20px] !pl-[20px] !pt-0">
              <RejectionReasonsSelector
                isDisabled={!userCanReview}
                selectedReasons={state.selectedRejectionReasons}
                setSelectedReasons={(reasons) => {
                  dispatchAndSave({ type: 'SET_REJECTION_REASONS', payload: reasons });
                }}
              />
            </div>
          )}
          <div className="flex justify-center !pt-[50px]">
            <Button
              className="!w-32"
              sdsStyle="square"
              sdsType="primary"
              endIcon={<Icon sdsIcon="ChevronRight" sdsSize="xs" />}
              onClick={handleNext}
            >
              Next Tomo
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
