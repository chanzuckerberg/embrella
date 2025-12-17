import { useReducer, useEffect, useCallback, useState } from 'react';
import { TopBar } from './components/TopBar';
import { SideBar } from './components/SideBar';
import { QualityControls } from './components/QualityControls';
import { ObjectLabelsSelector } from './components/ObjectLabelsSelector';
import { RejectionReasonsSelector } from './components/RejectionReasonsSelector';
import { OmeZarrImageViewer } from '../../../idetik/packages/react/src/components/viewers/OmeZarrImageViewer';
import { getRegionFromZattrs } from './utils';
import { Region } from '../../../idetik/packages/core/src/data/region';
import { useHotkeys } from 'react-hotkeys-hook';
import { Button, Icon } from '@czi-sds/components';
import { fetchResource, postResource } from '@app/common/queries/fetchResource';
import { getRequestURLWithPathParams, getRequestURL } from '@app/common/queries/utils';
import { DJANGO_URL } from '@app/common/constants/api';
// import { UserContext } from '@app/common/context/UserProvider';
// import { PermissionBanner } from './components/PermissionBanner';
import { Review, ReviewTomogramDetail } from './types';
import { useIdetik } from '../../../idetik/packages/react/src/components/hooks/useIdetik';

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
  contrastRange: [number, number]; // Dynamic range for the slider
}

const initialState = (firstTomogramId: string): TomogramState => ({
  selectedTomogramId: firstTomogramId,
  detail: null,
  quality: 'pending',
  objectLabels: [],
  rejectionReasons: [],
  saveState: 'idle',
  contrastLimits: [-0.05, 0.05],
  contrastRange: [-0.05, 0.05],
});

type TomogramAction =
  | { type: 'SET_DETAIL'; payload: ReviewTomogramDetail | null }
  | { type: 'SET_QUALITY'; payload: string }
  | { type: 'SET_OBJECT_LABELS'; payload: string[] }
  | { type: 'SET_REJECTION_REASONS'; payload: string[] }
  | { type: 'SET_SAVE_STATE'; payload: 'idle' | 'saving' | 'saved' | 'failed' }
  | { type: 'SET_CONTRAST_LIMITS'; payload: [number, number] }
  | { type: 'SET_CONTRAST_RANGE'; payload: [number, number] }
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
      // Validate that contrast limits are strictly increasing
      if (action.payload[0] >= action.payload[1]) {
        console.warn('Invalid contrast limits received, keeping current values:', action.payload);
        return state;
      }
      return { ...state, contrastLimits: action.payload };
    case 'SET_CONTRAST_RANGE':
      // Validate that contrast range is strictly increasing
      if (action.payload[0] >= action.payload[1]) {
        console.warn('Invalid contrast range received, keeping current values:', action.payload);
        return state;
      }
      return { ...state, contrastRange: action.payload };
    case 'SET_SELECTED_TOMOGRAM':
      return { ...state, selectedTomogramId: action.payload };
    default:
      return state;
  }
}

export const TomogramViewerView = ({ review, onReviewUpdate }: TomogramViewerProps) => {
  // Initialize hooks at the top level (before any conditional returns)
  const firstTomogramId = review.tomograms?.[0]?.tomogramId || '';
  const [state, dispatch] = useReducer(reducer, initialState(firstTomogramId));
  const [region, setRegion] = useState<Region | null>(null);
  // const currentUser = useContext(UserContext);
  const { isInitialized, imageSeriesLayer, channels } = useIdetik();
  // Commented out to allow everyone write access
  // const userCanReview = currentUser?.id === review.owner.id;
  const userCanReview = true; // Everyone can review now
  const currentIndex = review.tomograms?.findIndex((t) => t.tomogramId === state.selectedTomogramId) ?? -1;
  const reviewedTomograms = review.tomograms?.filter((tomo) => tomo.status !== 'pending').length ?? 0;

  const handleContrastLimitsChange = useCallback(
    (newLimits: [number, number]) => {
      // Validate that contrast limits are strictly increasing
      if (newLimits[0] >= newLimits[1]) {
        console.warn('Contrast limits must be strictly increasing, ignoring update:', newLimits);
        return;
      }

      dispatch({ type: 'SET_CONTRAST_LIMITS', payload: newLimits });

      // Update the image layer's contrast limits if available
      if (isInitialized && imageSeriesLayer && channels.length > 0) {
        const updatedChannels = [...channels];
        updatedChannels[0] = {
          ...updatedChannels[0],
          contrastLimits: newLimits,
        };
        imageSeriesLayer.setChannelProps(updatedChannels);
      }
    },
    [isInitialized, imageSeriesLayer, channels]
  );

  const saveTomogram = async () => {
    if (!userCanReview) return;
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
    if (!review.tomograms || nextIndex < 0 || nextIndex >= review.tomograms.length) return;
    dispatch({ type: 'SET_SELECTED_TOMOGRAM', payload: review.tomograms[nextIndex].tomogramId });
  };

  // Function to download review results
  const downloadReviewResults = async () => {
    // First save the current tomogram to ensure all changes are saved
    await saveTomogram();

    const reviewIdNoDashes = review.reviewId.replace(/-/g, '');
    const url = `${DJANGO_URL}/api/reviews/${reviewIdNoDashes}/export?reviewedOnly=true`;

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // For a downloadable file:
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `${review.reviewName}-results.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(downloadUrl);
      alert('Review results downloaded. Only reviewed tomograms are included in the report.');
    } catch (error) {
      console.error('Failed to download review results:', error);
      alert('Failed to download review results. Please try again.');
    }
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

      // Use contrast limits from API response if available, otherwise use default
      if (detail.contrastLimits) {
        // Validate that the API contrast limits are strictly increasing
        if (detail.contrastLimits[0] < detail.contrastLimits[1]) {
          dispatch({ type: 'SET_CONTRAST_LIMITS', payload: detail.contrastLimits });
          // Set the contrast range to be wider than the limits for better slider control
          const range = detail.contrastLimits;
          const padding = (range[1] - range[0]) * 1.0; // 100% padding for wider range
          const contrastRange: [number, number] = [range[0] - padding, range[1] + padding];
          dispatch({ type: 'SET_CONTRAST_RANGE', payload: contrastRange });
        } else {
          console.warn('Invalid contrast limits from API, using default:', detail.contrastLimits);
        }
      } else {
        // Fallback: set a reasonable contrast range based on reconstruction type
        const defaultRange: [number, number] = [-0.1, 0.1];
        dispatch({ type: 'SET_CONTRAST_RANGE', payload: defaultRange });
      }

      if (detail.zarrPath) {
        const region = await getRegionFromZattrs(detail.zarrPath);
        setRegion(region);
      }
    };
    loadDetail();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.selectedTomogramId, review.reviewId]);

  useHotkeys('a', () => dispatch({ type: 'SET_QUALITY', payload: 'accepted' }));
  useHotkeys('r', () => dispatch({ type: 'SET_QUALITY', payload: 'rejected' }));
  useHotkeys('u', () => dispatch({ type: 'SET_QUALITY', payload: 'uncertain' }));
  useHotkeys('e', () => dispatch({ type: 'SET_QUALITY', payload: 'exemplary' }));
  useHotkeys('left', () => changeTomogram(-1));
  useHotkeys('right', () => changeTomogram(1));

  if (!review.tomograms || review.tomograms.length === 0) {
    return (
      <div className="w-full h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-bold mb-2">No Tomograms Available</h2>
          <p className="text-gray-600">There are no tomograms to review in this review set.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-screen flex flex-col items-stretch bg-white">
      <TopBar saveState={state.saveState} />
      {/* Commented out to allow everyone write access */}
      {/* {!userCanReview && <PermissionBanner ownerName={review.owner.name} />} */}
      <div className="flex-auto flex min-h-0 border-t border-gray-300">
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
          contrastRange={state.contrastRange}
        />
        <div className="flex-auto flex flex-col p-6 items-center justify-center border-x-[2px] border-gray-300 bg-gray-200">
          {state.detail?.zarrPath !== undefined && region !== null && (
            <OmeZarrImageViewer
              sourceUrl={state.detail.zarrPath}
              region={region}
              fallbackContrastLimits={state.contrastLimits}
              resolutionLevel={state.detail.reconstructionType?.toLowerCase() === 'sart' ? 0 : 1}
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
                availableObjects={review.availableAnnotationObjects}
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
          <div className="flex justify-center gap-4 !pt-[50px]">
            <Button
              disabled={state.saveState === 'saving'}
              className="!w-32"
              sdsStyle="square"
              sdsType="secondary"
              startIcon={<Icon sdsIcon="ChevronLeft" sdsSize="xs" />}
              onClick={() => changeTomogram(-1)}
            >
              Previous Tomo
            </Button>
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
          <div className="flex justify-center !pt-[20px]">
            <Button
              disabled={state.saveState === 'saving' || reviewedTomograms < 1}
              className="!w-60"
              sdsStyle="square"
              sdsType="secondary"
              onClick={downloadReviewResults}
            >
              Download Review
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
