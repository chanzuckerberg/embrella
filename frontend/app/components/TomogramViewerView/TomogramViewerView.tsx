import { useReducer, useEffect, useCallback, useContext, useState } from 'react';
import { TopBar } from './components/TopBar';
import { SideBar } from './components/SideBar';
import { QualityControls } from './components/QualityControls';
import { ObjectLabelsSelector } from './components/ObjectLabelsSelector';
import { RejectionReasonsSelector } from './components/RejectionReasonsSelector';
import { OmeZarrImageViewer } from '../../../imaging-active-learning/packages/react/src/components/viewers/OmeZarrImageViewer';
import { getRegionFromZattrs } from './utils';
import { Region } from '../../../imaging-active-learning/packages/core/src/data/region';
import { useHotkeys } from 'react-hotkeys-hook';
import { useIdetik } from '../../../imaging-active-learning/packages/react/src/components/hooks';
import { Button, Icon } from '@czi-sds/components';
import { fetchResource, postResource } from '@app/common/queries/fetchResource';
import { getRequestURLWithPathParams, getRequestURL } from '@app/common/queries/utils';
import { DJANGO_URL } from '@app/common/constants/api';
import { UserContext } from '@app/common/context/UserProvider';
import { PermissionBanner } from './components/PermissionBanner';
import { Review, ReviewTomogramDetail } from './types';
import { AVAILABLE_ANNOTATION_OBJECTS } from '../CreateReviewView/CreateReviewView';

// Types
interface TomogramViewerProps {
  review: Review;
  onReviewUpdate: (review: Review) => void;
}

type QualityValue = 'pending' | 'accepted' | 'rejected' | 'uncertain' | 'exemplary';

interface TomogramState {
  selectedTomogramId: string;
  detail: ReviewTomogramDetail | null;
  quality: QualityValue;
  objectLabels: string[];
  rejectionReasons: string[];
  saveState: 'idle' | 'saving' | 'saved' | 'failed';
  contrastLimits: [number, number];
}

const initialState = (firstTomogramId: string): TomogramState => ({
  selectedTomogramId: firstTomogramId,
  detail: null,
  quality: 'pending',
  objectLabels: [],
  rejectionReasons: [],
  saveState: 'idle',
  contrastLimits: [-0.00001, 0.00001],
});

type TomogramAction =
  | { type: 'SET_DETAIL'; payload: ReviewTomogramDetail | null }
  | { type: 'SET_QUALITY'; payload: string }
  | { type: 'SET_OBJECT_LABELS'; payload: string[] }
  | { type: 'SET_REJECTION_REASONS'; payload: string[] }
  | { type: 'SET_SAVE_STATE'; payload: 'idle' | 'saving' | 'saved' | 'failed' }
  | { type: 'SET_CONTRAST_LIMITS'; payload: [number, number] }
  | { type: 'SET_SELECTED_TOMOGRAM'; payload: string };

function reducer(state: TomogramState, action: TomogramAction): TomogramState {
  switch (action.type) {
    case 'SET_DETAIL':
      return { ...state, detail: action.payload };
    case 'SET_QUALITY':
      return { ...state, quality: action.payload as QualityValue };
    case 'SET_OBJECT_LABELS':
      return { ...state, objectLabels: action.payload };
    case 'SET_REJECTION_REASONS':
      return { ...state, rejectionReasons: action.payload };
    case 'SET_SAVE_STATE':
      return { ...state, saveState: action.payload };
    case 'SET_CONTRAST_LIMITS':
      return { ...state, contrastLimits: action.payload };
    case 'SET_SELECTED_TOMOGRAM':
      return { ...state, selectedTomogramId: action.payload };
    default:
      return state;
  }
}

export const TomogramViewerView = ({ review, onReviewUpdate }: TomogramViewerProps) => {
  const [state, dispatch] = useReducer(reducer, initialState(review.tomograms[0].tomogramId));
  const [region, setRegion] = useState<Region | null>(null);
  const currentUser = useContext(UserContext);
  const userCanReview = currentUser?.id === review.owner.id;
  const currentIndex = review.tomograms.findIndex((t) => t.tomogramId === state.selectedTomogramId);

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

  const saveTomogram = async () => {
    dispatch({ type: 'SET_SAVE_STATE', payload: 'saving' });
    const url = getRequestURLWithPathParams(DJANGO_URL, '/api/reviews/:reviewId/tomograms/:tomogramId', {
      reviewId: review.reviewId,
      tomogramId: state.selectedTomogramId,
    });

    try {
      await postResource(url, {
        tomogramId: state.selectedTomogramId,
        quality: state.quality,
        objectLabels: state.objectLabels,
        rejectionReasons: state.rejectionReasons,
      });

      // fetch updated review object to update table state
      const updatedReviewRes = await fetchResource(getRequestURL(DJANGO_URL, `/api/reviews/${review.reviewId}`));
      const updatedReview = await updatedReviewRes.json();
      onReviewUpdate(updatedReview);

      dispatch({ type: 'SET_SAVE_STATE', payload: 'saved' });
    } catch {
      dispatch({ type: 'SET_SAVE_STATE', payload: 'failed' });
    }
  };

  const changeTomogram = async (indexDelta: number) => {
    await saveTomogram();
    const nextIndex = currentIndex + indexDelta;
    if (nextIndex < 0 || nextIndex >= review.tomograms.length) return;
    dispatch({ type: 'SET_SELECTED_TOMOGRAM', payload: review.tomograms[nextIndex].tomogramId });
  };

  useEffect(() => {
    const loadDetail = async () => {
      const url = getRequestURLWithPathParams(DJANGO_URL, '/api/reviews/:reviewId/tomograms/:tomogramId', {
        reviewId: review.reviewId,
        tomogramId: state.selectedTomogramId,
      });
      const res = await fetchResource(url);
      const detail = await res.json();
      dispatch({ type: 'SET_DETAIL', payload: detail });
      dispatch({ type: 'SET_QUALITY', payload: detail.existingReview?.quality || 'pending' });
      dispatch({ type: 'SET_OBJECT_LABELS', payload: detail.existingReview?.objectLabels || [] });
      dispatch({ type: 'SET_REJECTION_REASONS', payload: detail.existingReview?.rejectionReasons || [] });
      if (detail.zarrPath) {
        const region = await getRegionFromZattrs(detail.zarrPath);
        setRegion(region);
        if (imageSeriesLayer) {
          const updatedChannels = channels.map((channel) => ({
            ...channel,
            contrastLimits: state.contrastLimits,
          }));
          imageSeriesLayer.setChannelProps(updatedChannels);
        }
      }
    };
    loadDetail();
  }, [state.selectedTomogramId, channels, imageSeriesLayer, review.reviewId, state.contrastLimits]);

  useHotkeys('a', () => dispatch({ type: 'SET_QUALITY', payload: 'accepted' }));
  useHotkeys('r', () => dispatch({ type: 'SET_QUALITY', payload: 'rejected' }));
  useHotkeys('u', () => dispatch({ type: 'SET_QUALITY', payload: 'uncertain' }));
  useHotkeys('e', () => dispatch({ type: 'SET_QUALITY', payload: 'exemplary' }));
  useHotkeys('left', () => changeTomogram(-1));
  useHotkeys('right', () => changeTomogram(1));

  return (
    <div className="w-full h-screen flex flex-col items-stretch">
      <TopBar saveState={state.saveState} />
      {!userCanReview && <PermissionBanner ownerName={review.owner.name} />}
      <div className="flex-auto flex border-t border-gray-300">
        <SideBar
          tomogramDetail={state.detail}
          reviewName={review.reviewName}
          tomograms={review.tomograms}
          selectedTomogram={state.selectedTomogramId}
          currentIndex={currentIndex}
          onPrevious={() => changeTomogram(-1)}
          onNext={() => changeTomogram(1)}
          onSelectTomogram={(id) => dispatch({ type: 'SET_SELECTED_TOMOGRAM', payload: id })}
          contrastLimits={state.contrastLimits}
          onContrastLimitsChange={handleContrastLimitsChange}
        />
        <div className="flex-auto flex flex-col p-6 items-center justify-center border-x-[2px] border-gray-300 bg-gray-200">
          {state.detail?.zarrPath !== undefined && region !== null && (
            <OmeZarrImageViewer
              sourceUrl={state.detail.zarrPath}
              region={region}
              fallbackContrastLimits={state.contrastLimits}
              resolutionLevel={2}
              seriesDimensionName="z"
              shouldLoadMiddleZ
              shouldAutoLoadAllSlices
              classNames={{ root: 'bg-dark-sds-color-primitive-gray-100' }}
            />
          )}
        </div>
        <div className="flex flex-col gap-3">
          <div className="shrink-0 !pt-[20px] !pr-[20px] !pl-[20px] !pb-[20px]">
            <QualityControls
              isDisabled={!userCanReview}
              selectedQuality={state.quality}
              onAccept={() => dispatch({ type: 'SET_QUALITY', payload: 'accepted' })}
              onReject={() => dispatch({ type: 'SET_QUALITY', payload: 'rejected' })}
              onUncertain={() => dispatch({ type: 'SET_QUALITY', payload: 'uncertain' })}
              onExemplary={() => dispatch({ type: 'SET_QUALITY', payload: 'exemplary' })}
            />
          </div>
          {(state.quality === 'accepted' || state.quality === 'uncertain' || state.quality === 'exemplary') && (
            <div className="shrink-0 !pb-[20px] !pr-[20px] !pl-[20px] !pt-0">
              <ObjectLabelsSelector
                isDisabled={!userCanReview}
                availableObjects={AVAILABLE_ANNOTATION_OBJECTS}
                selectedObjects={state.objectLabels}
                setSelectedObjects={(labels) => dispatch({ type: 'SET_OBJECT_LABELS', payload: labels })}
              />
            </div>
          )}
          {state.quality === 'rejected' && (
            <div className="shrink-0 !pb-[20px] !pr-[20px] !pl-[20px] !pt-0">
              <RejectionReasonsSelector
                isDisabled={!userCanReview}
                selectedReasons={state.rejectionReasons}
                setSelectedReasons={(reasons) => dispatch({ type: 'SET_REJECTION_REASONS', payload: reasons })}
              />
            </div>
          )}
          <div className="flex justify-center !pt-[50px]">
            <Button
              disabled={state.saveState === 'saving'}
              className="!w-32"
              sdsStyle="square"
              sdsType="primary"
              endIcon={<Icon sdsIcon="ChevronRight" sdsSize="xs" />}
              onClick={() => changeTomogram(1)}
            >
              Next Tomo
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
