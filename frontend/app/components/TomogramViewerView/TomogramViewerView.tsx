'use client';

import { useReducer, useEffect, useCallback, useState, useMemo, useRef, startTransition } from 'react';
import { TopBar } from './components/TopBar';
import { SideBar } from './components/SideBar';
import { QualityControls } from './components/QualityControls';
import { ObjectLabelsSelector } from './components/ObjectLabelsSelector';
import { RejectionReasonsSelector } from './components/RejectionReasonsSelector';
import { OmeZarrChunkedImageViewer, IdetikProvider } from '@idetik/react';
import { ChunkedImageLayer, ChannelsEnabled, createImageSourcePolicy } from '@idetik/core';
import { getRegionFromZattrs, getZAxisMetadata } from './utils';
import { useHotkeys } from 'react-hotkeys-hook';
import { Button, Icon } from '@czi-sds/components';
import { fetchResource, postResource } from '@app/common/queries/fetchResource';
import { getRequestURLWithPathParams, getRequestURL } from '@app/common/queries/utils';
import { DJANGO_URL } from '@app/common/constants/api';
// import { UserContext } from '@app/common/context/UserProvider';
// import { PermissionBanner } from './components/PermissionBanner';
import { Review, ReviewTomogramDetail } from './types';

// Wrapper component - provider is now inside the inner component to allow remounting
export const TomogramViewerView = (props: TomogramViewerProps) => {
  return <TomogramViewerViewInner {...props} />;
};

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

const TomogramViewerViewInner = ({ review, onReviewUpdate }: TomogramViewerProps) => {
  const firstTomogramId = review.tomograms?.[0]?.tomogramId ?? '';
  const [state, dispatch] = useReducer(reducer, initialState(firstTomogramId));

  // Key the provider to the selected tomogram ID so it remounts when switching
  // This resets the provider's isReady state, allowing the new canvas to initialize
  const providerKey = state.selectedTomogramId;

  return (
    <IdetikProvider key={providerKey}>
      <TomogramViewerContent review={review} onReviewUpdate={onReviewUpdate} state={state} dispatch={dispatch} />
    </IdetikProvider>
  );
};

// Inner component that uses the IdetikProvider context
const TomogramViewerContent = ({
  review,
  onReviewUpdate,
  state,
  dispatch,
}: TomogramViewerProps & { state: TomogramState; dispatch: React.Dispatch<TomogramAction> }) => {
  const [currentZIndex, setCurrentZIndex] = useState<number>(0); // Track current z-slice
  const [zAxisMetadata, setZAxisMetadata] = useState<{ min: number; max: number; count: number } | null>(null);
  const [, setZMaxIndex] = useState<number | undefined>(undefined);
  const [isLoadingTomogram, setIsLoadingTomogram] = useState<boolean>(false); // Track loading state to prevent double mounting
  const [shouldRenderViewer, setShouldRenderViewer] = useState<boolean>(true); // Control when viewer is in the DOM (start true for initial load)
  const viewerMountKey = useRef<number>(0); // Unique key counter to force remounts
  const [channelLayer, setChannelLayer] = useState<ChannelsEnabled | null>(null);
  const [extraControlProps, setExtraControlProps] = useState<Array<{ label: string; contrastRange: [number, number] }>>(
    []
  );
  const previousTomogramId = useRef<string>(state.selectedTomogramId); // Track previous tomogram to detect changes
  // const currentUser = useContext(UserContext);
  // Commented out to allow everyone write access
  // const userCanReview = currentUser?.id === review.owner.id;
  const userCanReview = true; // Everyone can review now
  const currentIndex = review.tomograms.findIndex((t) => t.tomogramId === state.selectedTomogramId);
  const reviewedTomograms = review.tomograms.filter((tomo) => tomo.status !== 'pending').length;

  // Calculate z prop object - will be recalculated when switching tomograms
  // This ensures a fresh remount when selectedTomogramId changes
  const zProp = useMemo(() => {
    if (!zAxisMetadata || zAxisMetadata.count === 0) return undefined;
    // Ensure both initIndex and index are within valid bounds
    const maxIndex = zAxisMetadata.count - 1;
    const initIndex = Math.max(0, Math.min(Math.floor(zAxisMetadata.count / 2), maxIndex));
    const clampedZIndex = Math.max(0, Math.min(currentZIndex, maxIndex));
    return {
      initIndex,
      index: clampedZIndex,
      setMaxIndex: setZMaxIndex,
    };
  }, [zAxisMetadata, currentZIndex]); // zAxisMetadata and currentZIndex already change when tomogram changes

  // Calculate fallbackContrastLimits - will be recalculated when switching tomograms
  const fallbackContrastLimits = useMemo((): [number, number] => {
    return state.detail?.contrastLimits || [-0.05, 0.05];
  }, [state.detail?.contrastLimits]); // state.detail already changes when tomogram changes

  // Static classNames - safe to memoize
  // Include h-full to ensure the canvas takes full height
  // Hide the built-in Channel Controls overlay (we render it in the sidebar instead)
  const viewerClassNames = useMemo(
    () => ({
      root: 'bg-dark-sds-color-primitive-gray-100 h-full w-full [&_.absolute.top-0.left-0.z-10]:hidden',
    }),
    []
  );

  // Custom policy with LOD min set to 1 (skip highest resolution level 0)
  const customPolicy = useMemo(
    () =>
      createImageSourcePolicy({
        prefetch: { x: 0, y: 0, z: 200 },
        priorityOrder: ['fallbackVisible', 'visibleCurrent', 'fallbackBackground', 'prefetchSpace',  'prefetchTime'],
        lod: {
          min: 0,
          max: 1,
          bias: 1.0,
        },
      }),
    []
  );

  // Handle z-slice navigation - just update state
  // The component's slice update effect will handle z.index prop changes without re-initialization
  const handleZIndexChange = useCallback(
    (newZIndex: number) => {
      if (newZIndex !== currentZIndex && zAxisMetadata) {
        setCurrentZIndex(newZIndex);
      }
    },
    [currentZIndex, zAxisMetadata]
  );

  // Handle layer creation - store reference for ChannelControlsList
  const handleLayerCreated = useCallback((layers: ChunkedImageLayer[]) => {
    // Use the first layer if multiple layers are created
    const layer = layers[0];
    if (!layer) return;

    setChannelLayer(layer);
    // Set extraControlProps for the channel controls
    const channels = layer.channelProps;
    if (channels && channels.length > 0) {
      const contrastLimits = channels[0].contrastLimits || [-0.05, 0.05];
      const padding = (contrastLimits[1] - contrastLimits[0]) * 2;
      setExtraControlProps([
        {
          label: 'Tomogram',
          contrastRange: [contrastLimits[0] - padding, contrastLimits[1] + padding],
        },
      ]);
    }
  }, []);

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
    // Detect when tomogram changes
    const tomogramChanged = previousTomogramId.current !== state.selectedTomogramId;
    previousTomogramId.current = state.selectedTomogramId;

    const loadDetail = async () => {
      // If tomogram changed, completely remove viewer from DOM first
      if (tomogramChanged) {
      setIsLoadingTomogram(true);
        setShouldRenderViewer(false); // Remove viewer from DOM immediately
      dispatch({ type: 'SET_DETAIL', payload: null });

        // Reset z-index state when switching tomograms to prevent out-of-bounds errors
      setZAxisMetadata(null);
      setCurrentZIndex(0);

        // Reset channel layer state
      setChannelLayer(null);
      setExtraControlProps([]);

        // Wait for React to fully unmount the old viewer
        // Use multiple animation frames to ensure cleanup completes
        await new Promise<void>((resolve) => {
          requestAnimationFrame(() => {
            requestAnimationFrame(() => {
              requestAnimationFrame(() => {
                resolve();
              });
            });
          });
        });
      }

      const url = getRequestURLWithPathParams(DJANGO_URL, '/api/reviews/:reviewId/tomograms/:tomogramId', {
        reviewId: review.reviewId,
        tomogramId: state.selectedTomogramId,
      });
      const res = await fetchResource(url);
      const detail = await res.json();

      // Increment mount key to ensure a fresh remount
      if (tomogramChanged) {
        viewerMountKey.current += 1;
      }

      dispatch({ type: 'SET_DETAIL', payload: detail });

      // Use startTransition to ensure state updates happen after unmount
      if (tomogramChanged) {
        startTransition(() => {
          setShouldRenderViewer(true); // Add viewer back to DOM
      setIsLoadingTomogram(false);
        });
      } else {
        setIsLoadingTomogram(false);
      }
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
        // Get z-axis metadata and start with middle z-slice
        // z axis metadata specifies the valid range of z indices
        const zMeta = await getZAxisMetadata(detail.zarrPath);
        setZAxisMetadata(zMeta);

        // Ensure initial index is within valid bounds
        const initialZIndex = Math.max(0, Math.min(Math.floor(zMeta.count / 2), zMeta.count - 1));
        setCurrentZIndex(initialZIndex);
        setZMaxIndex(zMeta.count - 1);

        await getRegionFromZattrs(detail.zarrPath, initialZIndex);
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
          currentZIndex={currentZIndex}
          zAxisMetadata={zAxisMetadata || undefined}
          onZIndexChange={handleZIndexChange}
          channelLayer={channelLayer}
          extraControlProps={extraControlProps}
        />
        <div className="flex-auto flex flex-col p-6 border-x-[2px] border-gray-300 bg-gray-200 h-full">
          {shouldRenderViewer &&
            !isLoadingTomogram &&
            state.detail?.zarrPath !== undefined &&
            zAxisMetadata !== null &&
            zProp !== undefined && (
              <OmeZarrChunkedImageViewer
                key={`${state.detail.zarrPath}-${state.selectedTomogramId}-${viewerMountKey.current}`}
                sourceUrl={state.detail.zarrPath}
                z={zProp}
                fallbackContrastLimits={fallbackContrastLimits}
                classNames={viewerClassNames}
                onLayersCreated={handleLayerCreated}
                policy={customPolicy}
              />
            )}
          {(!shouldRenderViewer || isLoadingTomogram) && (
            <div className="text-center">
              <p className="text-gray-600">Loading tomogram...</p>
            </div>
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
