'use client';

import { useState, useEffect, useRef, useCallback, useReducer } from 'react';
import { TopBar } from './components/TopBar';
import { SideBar } from './components/SideBar';
import { Review, ReviewTomogramDetail } from './types';
import { QualityControls } from './components/QualityControls';
import { OmeZarrImageViewer } from '../../../imaging-active-learning/packages/react/src/components/viewers/OmeZarrImageViewer';
import { Region } from '../../../imaging-active-learning/packages/core/src/data/region';
import { getRegionFromZattrs } from './utils';
import { useIdetik } from '../../../imaging-active-learning/packages/react/src/components/hooks';
import { API, MOCKED_APIS, POST_API, MOCKED_POST_APIS } from '../../../app/common/constants/api';
import { RejectionReasonsSelector } from './components/RejectionReasonsSelector';
import { ObjectLabelsSelector } from './components/ObjectLabelsSelector';
import { AVAILABLE_ANNOTATION_OBJECTS } from '../CreateReviewView/CreateReviewView';
import { Button, Icon } from '@czi-sds/components';

interface TomogramViewerProps {
  review: Review;
}

interface TomogramState {
  selectedTomogram: string | undefined;
  tomogramDetail: ReviewTomogramDetail | null;
  contrastLimits: [number, number];
  selectedRejectionReasons: string[];
  selectedQuality: 'accepted' | 'rejected' | 'uncertain' | 'pending';
  selectedObjectLabels: string[];
  saveState?: 'saving' | 'saved' | 'failed';
}

type TomogramAction =
  | { type: 'SET_SELECTED_TOMOGRAM'; payload: string }
  | { type: 'SET_TOMOGRAM_DETAIL'; payload: ReviewTomogramDetail | null }
  | { type: 'SET_CONTRAST_LIMITS'; payload: [number, number] }
  | { type: 'SET_REJECTION_REASONS'; payload: string[] }
  | { type: 'SET_QUALITY'; payload: 'accepted' | 'rejected' | 'uncertain' | 'pending' }
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

  const layerCreatedTime = useRef<number | undefined>(undefined);
  const loadAllSlicesClickedTime = useRef<number | undefined>(undefined);

  const seriesDimensionName = 'z'; // TODO: get from zarr metadata
  const { imageSeriesLayer, channels } = useIdetik();

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

  const handleLayerCreated = useCallback(() => {
    layerCreatedTime.current = performance.now();
    console.log(`Layer created at ${layerCreatedTime.current}`);
  }, []);

  const handleFirstSliceLoaded = useCallback(() => {
    if (layerCreatedTime.current !== undefined) {
      const time = performance.now() - layerCreatedTime.current;
      console.log(`First slice loaded after ${time} ms`);
    } else {
      console.log('First slice loaded, but layer created time is undefined');
    }
  }, []);

  const handleLoadAllSlicesClicked = useCallback(() => {
    loadAllSlicesClickedTime.current = performance.now();
    console.log(`Load all slices clicked at ${loadAllSlicesClickedTime.current}`);
  }, []);

  const handleAllSlicesLoaded = useCallback(() => {
    if (loadAllSlicesClickedTime.current !== undefined) {
      const time = performance.now() - loadAllSlicesClickedTime.current;
      console.log(`All slices loaded after ${time} ms`);
    } else {
      console.log('All slices loaded, but load all slices clicked time is undefined');
    }
  }, []);

  const handleLoadAllSlicesAborted = useCallback(() => {
    if (loadAllSlicesClickedTime.current !== undefined) {
      const time = performance.now() - loadAllSlicesClickedTime.current;
      console.log(`Load all slices aborted after ${time} ms`);
    } else {
      console.log('Load all slices aborted, but load all slices clicked time is undefined');
    }
  }, []);

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

      const selectedTomogramStatus = review.tomograms.find((t) => t.tomogramId === state.selectedTomogram)?.status;
      const allowedTomograms = ['tomo_001', 'tomo_002', 'tomo_003', 'tomo_004'];

      const tomogramIdToUse = allowedTomograms.includes(state.selectedTomogram)
        ? state.selectedTomogram
        : getTomogramIdForStatus(selectedTomogramStatus);

      const url = `/api/reviews/${review.reviewId}/tomograms/${tomogramIdToUse}`;
      const tomogramDetail = MOCKED_APIS[API.TOMOGRAM_DETAIL](url);

      updateTomogramState(tomogramDetail);
    }
    fetchTomogramDetail();
  }, [state.selectedTomogram, review.reviewId, review.tomograms]);

  // TODO: Debounce.
  const save = async (
    quality: 'accepted' | 'rejected' | 'uncertain' | 'pending',
    rejectionReasons?: string[],
    objectLabels?: string[]
  ) => {
    if (!state.selectedTomogram) return;
    dispatch({ type: 'SET_SAVE_STATE', payload: 'saving' });

    const payload = {
      tomogramId: state.selectedTomogram,
      quality,
      rejectionReasons,
      objectLabels,
    };

    // TODO: Real API.
    const saveResponse = await new Promise((resolve) =>
      setTimeout(() => {
        resolve(MOCKED_POST_APIS[POST_API.UPDATE_TOMOGRAM_REVIEW](payload));
      }, 1000)
    );
    if (saveResponse !== undefined) {
      dispatch({ type: 'SET_SAVE_STATE', payload: 'saved' });
    }
  };

  const dispatchAndSave = (value: TomogramAction): void => {
    dispatch(value);
    save(state.selectedQuality, state.selectedRejectionReasons, state.selectedObjectLabels);
  };

  return (
    <div className="w-full h-screen flex flex-col items-stretch">
      <TopBar saveState={state.saveState} onMarkComplete={() => console.log('Mark as complete')} />
      <div className="flex-auto flex border-t border-gray-400">
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
        <div className="flex-auto flex flex-col p-6 rounded items-center justify-center">
          {state.tomogramDetail?.zarrPath !== undefined && (
            <OmeZarrImageViewer
              sourceUrl={state.tomogramDetail.zarrPath}
              region={region ?? []}
              seriesDimensionName={seriesDimensionName}
              allSlicesSizeEstimate="250 MB"
              fallbackContrastLimits={state.contrastLimits}
              classNames={{
                root: 'bg-dark-sds-color-primitive-gray-100',
              }}
              onLayerCreated={handleLayerCreated}
              onFirstSliceLoaded={handleFirstSliceLoaded}
              onLoadAllSlicesClicked={handleLoadAllSlicesClicked}
              onAllSlicesLoaded={handleAllSlicesLoaded}
              onLoadAllSlicesAborted={handleLoadAllSlicesAborted}
            />
          )}
        </div>
        <div className="flex flex-col gap-3">
          <div className="shrink-0 !pt-[20px] !pr-[20px] !pl-[20px] !pb-[20px]">
            <QualityControls
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
            />
          </div>
          {(state.selectedQuality === 'accepted' || state.selectedQuality === 'uncertain') && (
            <div className="shrink-0 !pb-[20px] !pr-[20px] !pl-[20px] !pt-0">
              <ObjectLabelsSelector
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
