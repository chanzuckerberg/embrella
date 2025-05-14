/* eslint-disable @typescript-eslint/no-unused-vars */

'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { TopBar } from './components/TopBar';
import { SideBar } from './components/SideBar';
import { Review, ReviewTomogramDetail, TomogramDetail } from './types';
import { QualityControls } from './components/QualityControls';
import { OmeZarrImageViewer } from '../../../imaging-active-learning/packages/react/src/components/viewers/OmeZarrImageViewer';
import { Region } from '../../../imaging-active-learning/packages/core/src/data/region';
import { getRegionFromZattrs } from './utils';

interface TomogramViewerProps {
  review: Review;
}

const sourceUrl =
  'https://onsite.czbiohub.org/group.czii/ashley.anderson/hitl-sample/aretomo3/vol002/Position_10_Vol.zarr';

export const TomogramViewerView = ({ review }: TomogramViewerProps) => {
  const [region, setRegion] = useState<Region | null>(null);
  const imageUrl = `${sourceUrl}`;

  const layerCreatedTime = useRef<number | undefined>(undefined);
  const loadAllSlicesClickedTime = useRef<number | undefined>(undefined);

  const [selectedTomogram, setSelectedTomogram] = useState<string | undefined>(review.tomograms[0]?.tomogramId);
  const [tomogramDetail, setTomogramDetail] = useState<ReviewTomogramDetail | null>(null);
  const [zPosition, setZPosition] = useState(0);
  const [seriesDimensionName, setSeriesDimensionName] = useState('Z');
  const [contrast, setContrast] = useState<[number, number]>([-0.00001, 0.00001]);

  useEffect(() => {
    const fetchRegion = async () => {
      const region = await getRegionFromZattrs(imageUrl);
      setRegion(region);
    };
    fetchRegion();
  }, [imageUrl]);

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

  const currentIndex = selectedTomogram ? review.tomograms.findIndex((t) => t.tomogramId === selectedTomogram) : -1;

  const handlePrevious = () => {
    if (currentIndex > 0) {
      setSelectedTomogram(review.tomograms[currentIndex - 1].tomogramId);
    }
  };

  const handleNext = () => {
    if (currentIndex < review.tomograms.length - 1) {
      setSelectedTomogram(review.tomograms[currentIndex + 1].tomogramId);
    }
  };

  useEffect(() => {
    const fetchTomogramDetail = async () => {
      if (!selectedTomogram) return;

      const mockResponse: TomogramDetail = {
        tomogramId: selectedTomogram,
        displayName: `Grid5_${selectedTomogram}`,
        zarrPath: `https://review-static.czbiohub.org/zarrs/Grid5_2025-04-10/${selectedTomogram}.zarr`,
        existingReview: {
          quality: 'uncertain' as const,
        },
      };

      setTomogramDetail(mockResponse);
    };
    fetchTomogramDetail();
  }, [selectedTomogram]);

  return (
    <div className="flex flex-col items-stretch min-h-screen gap-8">
      <TopBar onMarkComplete={() => console.log('Mark as complete')} />
      <div className="flex-auto flex">
        <SideBar
          reviewName={review.reviewName}
          tomograms={review.tomograms}
          selectedTomogram={selectedTomogram}
          tomogramDetail={tomogramDetail}
          currentIndex={currentIndex}
          onPrevious={handlePrevious}
          onNext={handleNext}
          onSelectTomogram={setSelectedTomogram}
          contrast={contrast}
          onContrastChange={setContrast}
        />
        <div className="flex-auto flex flex-col p-6 rounded">
          {selectedTomogram && region ? (
            <>
              <div className="flex-1 flex items-center justify-center border-r border-l">
                <OmeZarrImageViewer
                  sourceUrl={imageUrl}
                  region={region}
                  seriesDimensionName="z"
                  allSlicesSizeEstimate="250 MB"
                  classNames={{
                    root: 'bg-dark-sds-color-primitive-gray-100',
                  }}
                  onLayerCreated={handleLayerCreated}
                  onFirstSliceLoaded={handleFirstSliceLoaded}
                  onLoadAllSlicesClicked={handleLoadAllSlicesClicked}
                  onAllSlicesLoaded={handleAllSlicesLoaded}
                  onLoadAllSlicesAborted={handleLoadAllSlicesAborted}
                />
              </div>
            </>
          ) : (
            <div className="p-6 bg-white rounded">Select a tomogram to view</div>
          )}
        </div>
        <div className="basis-[250px] shrink-0 !p-[20px]">
          <QualityControls
            onAccept={() => console.log('Accept')}
            onReject={() => console.log('Reject')}
            onUncertain={() => console.log('Uncertain')}
          />
        </div>
      </div>
    </div>
  );
};
