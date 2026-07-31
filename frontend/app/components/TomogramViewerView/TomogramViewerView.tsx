'use client';

import { useReducer, useEffect, useCallback, useState, useMemo } from 'react';
import { TopBar } from './components/TopBar';
import { SideBar } from './components/SideBar';
import { AssessmentPanel } from './components/AssessmentPanel';
import { MobileHeaderBar } from './components/MobileHeaderBar';
import { SliderControls } from './components/SideBar/components/SliderControls';
import { OmeZarrChunkedImageViewer, IdetikProvider } from '@idetik/react';
import { ChunkedImageLayer, ChannelsEnabled, createImageSourcePolicy } from '@idetik/core';
import { getZattrsData, getZAxisMetadata } from './utils';
import { useHotkeys } from 'react-hotkeys-hook';
import './TomogramViewerView.css';
import { Button, Icon } from '@czi-sds/components';
import { Drawer } from '@mui/material';
import { fetchResource, postResource } from '@app/common/queries/fetchResource';
import { getRequestURLWithPathParams, getRequestURL } from '@app/common/queries/utils';
import { DJANGO_URL } from '@app/common/constants/api';
import { useIsNarrowViewport } from '@app/common/hooks/useIsNarrowViewport';
import { QualityValue, Review, ReviewTomogramDetail, SaveState } from './types';

// Wrapper component - provider is now inside the inner component to allow remounting
export const TomogramViewerView = (props: TomogramViewerProps) => {
  return <TomogramViewerViewInner {...props} />;
};

// Types

interface TomogramViewerProps {
  review: Review;
  onReviewUpdate: (review: Review) => void;
}

interface TomogramState {
  selectedTomogramId: string;
  detail: ReviewTomogramDetail | null;
  quality: QualityValue;
  objectLabels: string[];
  rejectionReasons: string[];
  saveState: SaveState;
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
  | { type: 'SET_SAVE_STATE'; payload: SaveState }
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
  const isNarrow = useIsNarrowViewport();
  const [menuOpen, setMenuOpen] = useState(false);
  const [currentZIndex, setCurrentZIndex] = useState<number>(0); // Track current z-slice
  const [zAxisMetadata, setZAxisMetadata] = useState<{ min: number; max: number; count: number } | null>(null);
  const [, setZMaxIndex] = useState<number | undefined>(undefined);
  const [channelLayer, setChannelLayer] = useState<ChannelsEnabled | null>(null);
  const [extraControlProps, setExtraControlProps] = useState<Array<{ label: string; contrastRange: [number, number] }>>(
    []
  );
  // prevents stale closure in IdetikProvider's canvasRefCallback from seeing
  // a dangling runtime during the unmount-remount sequence.
  const [isStableMount, setIsStableMount] = useState(false);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsStableMount(true);
    return () => setIsStableMount(false);
  }, []);

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
      root: 'bg-dark-sds-color-primitive-gray-100 h-full w-full',
    }),
    []
  );

  // Custom policy better for both 2d rechunked and 3d chunked data. Our AreTomo runs are chunked into 128
  const customPolicy = useMemo(
    () =>
      createImageSourcePolicy({
        prefetch: { x: 0, y: 0, z: 128 },
        priorityOrder: ['fallbackVisible', 'visibleCurrent', 'fallbackBackground', 'prefetchTime', 'prefetchSpace'],
        lod: {
          min: 0,
          bias: 0.5,
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
    let cancelled = false;

    // Reset state for new tomogram (each instance starts fresh due to key-based remounting)
    /* eslint-disable react-hooks/set-state-in-effect -- resets paired with the async detail fetch below */
    setZAxisMetadata(null);
    setCurrentZIndex(0);
    setChannelLayer(null);
    setExtraControlProps([]);
    /* eslint-enable react-hooks/set-state-in-effect */

    const loadDetail = async () => {
      const url = getRequestURLWithPathParams(DJANGO_URL, '/api/reviews/:reviewId/tomograms/:tomogramId', {
        reviewId: review.reviewId,
        tomogramId: state.selectedTomogramId,
      });
      const res = await fetchResource(url);
      if (cancelled) return;
      const detail = await res.json();
      if (cancelled) return;

      dispatch({ type: 'SET_DETAIL', payload: detail });
      dispatch({ type: 'SET_QUALITY', payload: detail.existingReview?.quality || 'pending' });
      dispatch({ type: 'SET_OBJECT_LABELS', payload: detail.existingReview?.objectLabels || [] });
      dispatch({ type: 'SET_REJECTION_REASONS', payload: detail.existingReview?.rejectionReasons || [] });

      if (detail.zarrPath) {
        const zMeta = await getZAxisMetadata(detail.zarrPath);
        if (cancelled) return;
        setZAxisMetadata(zMeta);

        const initialZIndex = Math.max(0, Math.min(Math.floor(zMeta.count / 2), zMeta.count - 1));
        setCurrentZIndex(initialZIndex);
        setZMaxIndex(zMeta.count - 1);

        const zattrsData = await getZattrsData(detail.zarrPath, initialZIndex);
        if (cancelled) return;

        const contrastLimits = zattrsData.contrastLimits
          ? ([zattrsData.contrastLimits.low, zattrsData.contrastLimits.high] as [number, number])
          : detail.contrastLimits;

        if (contrastLimits && contrastLimits[0] < contrastLimits[1]) {
          dispatch({ type: 'SET_CONTRAST_LIMITS', payload: contrastLimits });
          const padding = (contrastLimits[1] - contrastLimits[0]) * 1.0;
          const contrastRange: [number, number] = [contrastLimits[0] - padding, contrastLimits[1] + padding];
          dispatch({ type: 'SET_CONTRAST_RANGE', payload: contrastRange });
        } else {
          const defaultRange: [number, number] = [-0.1, 0.1];
          dispatch({ type: 'SET_CONTRAST_RANGE', payload: defaultRange });
        }
      }
    };
    loadDetail();
    return () => {
      cancelled = true;
    };
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

  const sideBarProps = {
    tomogramDetail: state.detail,
    reviewName: review.reviewName,
    tomograms: review.tomograms,
    selectedTomogram: state.selectedTomogramId,
    currentIndex,
    onPrevious: () => changeTomogram(-1),
    onNext: () => changeTomogram(1),
    onSelectTomogram: (id: string) => dispatch({ type: 'SET_SELECTED_TOMOGRAM', payload: id }),
    currentZIndex,
    zAxisMetadata: zAxisMetadata || undefined,
    onZIndexChange: handleZIndexChange,
    channelLayer,
    extraControlProps,
  };

  const assessmentProps = {
    isDisabled: !userCanReview,
    isSaving: state.saveState === 'saving',
    quality: state.quality,
    availableAnnotationObjects: review.availableAnnotationObjects,
    objectLabels: state.objectLabels,
    rejectionReasons: state.rejectionReasons,
    canDownload: reviewedTomograms >= 1,
    onQualityChange: (quality: QualityValue) => dispatch({ type: 'SET_QUALITY', payload: quality }),
    onObjectLabelsChange: (labels: string[]) => dispatch({ type: 'SET_OBJECT_LABELS', payload: labels }),
    onRejectionReasonsChange: (reasons: string[]) => dispatch({ type: 'SET_REJECTION_REASONS', payload: reasons }),
    onPrevious: () => changeTomogram(-1),
    onNext: () => changeTomogram(1),
    onDownload: downloadReviewResults,
  };

  return (
    <div className="w-full h-screen max-lg:h-dvh flex flex-col items-stretch bg-white">
      <TopBar saveState={state.saveState} />
      {/* Permission banner intentionally disabled to allow everyone write access; kept for context. */}
      {/* eslint-disable-next-line sonarjs/no-commented-code */}
      {/* {!userCanReview && <PermissionBanner ownerName={review.owner.name} />} */}
      {isNarrow && (
        <MobileHeaderBar
          reviewName={review.reviewName}
          tomogramName={state.detail?.displayName ?? review.tomograms[currentIndex]?.position}
          currentIndex={currentIndex}
          totalTomograms={review.tomograms.length}
          onOpenMenu={() => setMenuOpen(true)}
        />
      )}
      <div className="flex-auto flex min-h-0 border-t border-gray-300">
        {/* Narrow screens render the sidebar and assessment panel inside the drawer below. */}
        {!isNarrow && <SideBar {...sideBarProps} />}
        <div className="flex-auto min-w-0 flex flex-col p-6 max-lg:!p-1 border-x-[2px] max-lg:border-x-0 border-gray-300 bg-gray-200 h-full max-lg:touch-none">
          {isStableMount && state.detail?.zarrPath !== undefined && zAxisMetadata !== null && zProp !== undefined ? (
            <OmeZarrChunkedImageViewer
              key={`${state.detail.zarrPath}-${state.selectedTomogramId}`}
              sourceUrl={state.detail.zarrPath}
              z={zProp}
              fallbackContrastLimits={fallbackContrastLimits}
              classNames={viewerClassNames}
              onLayersCreated={handleLayerCreated}
              scaleBar={{ visible: true, align: 'start' }}
              policy={customPolicy}
            />
          ) : (
            <div className="text-center">
              <p className="text-gray-600">Loading tomogram...</p>
            </div>
          )}
        </div>
        {!isNarrow && <AssessmentPanel {...assessmentProps} />}
      </div>
      {/* Z-slice navigation is the one control that has to stay reachable while
          scrubbing through a tomogram, so it gets a persistent bar of its own. */}
      {isNarrow && (
        <div className="shrink-0 border-t-[2px] border-gray-300 !px-[16px] !py-[10px]">
          <SliderControls
            compact
            currentZIndex={currentZIndex}
            zAxisMetadata={zAxisMetadata || undefined}
            onZIndexChange={handleZIndexChange}
          />
        </div>
      )}
      {isNarrow && (
        <Drawer
          anchor="left"
          open={menuOpen}
          onClose={() => setMenuOpen(false)}
          hideBackdrop={false}
          ModalProps={{ keepMounted: true }}
          PaperProps={{ sx: { width: 'min(80vw, 340px)', overflowY: 'auto' } }}
        >
          <div className="flex flex-row justify-end shrink-0 !px-[12px] !pt-[12px]">
            <Button
              sdsStyle="minimal"
              sdsType="secondary"
              aria-label="Close review controls"
              startIcon={<Icon sdsIcon="XMark" sdsSize="s" />}
              onClick={() => setMenuOpen(false)}
            >
              Close
            </Button>
          </div>
          <SideBar {...sideBarProps} showSliderSection={false} />
          <div className="border-t-[2px] border-gray-300">
            <AssessmentPanel {...assessmentProps} />
          </div>
        </Drawer>
      )}
    </div>
  );
};
