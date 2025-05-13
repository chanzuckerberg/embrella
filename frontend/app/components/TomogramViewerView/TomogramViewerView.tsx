/* eslint-disable @typescript-eslint/no-unused-vars */

'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { TopBar } from './components/TopBar';
import { SideBar } from './components/SideBar';
import { Button } from '@czi-sds/components';
import { Review, ReviewTomogramDetail } from './types';
import { QualityControls } from './components/QualityControls';
import { OmeZarrImageViewer } from '../../../imaging-active-learning/packages/react/src/components/viewers/OmeZarrImageViewer';
import { Region } from '../../../imaging-active-learning/packages/core/src/data/region';

interface TomogramViewerProps {
  review: Review;
}

const sourceUrl = 'https://public.czbiohub.org/organelle_box/datasets/A549/organelle_box_crop_v1.zarr';
const wellPath = 'ATG101/MeOH';
const region: Region = [
  { dimension: 'T', index: { type: 'point', value: 0 } },
  { dimension: 'C', index: { type: 'full' } },
  { dimension: 'Z', index: { type: 'full' } },
  { dimension: 'Y', index: { type: 'full' } },
  { dimension: 'X', index: { type: 'full' } },
];
const imagePaths = ['000000', '000001', '000002', '001000', '001001', '001002'];

export const TomogramViewerView = ({ review }: TomogramViewerProps) => {
  const [imageIndex, setImageIndex] = useState(0);
  const imagePath = imagePaths[imageIndex];
  const imageUrl = `${sourceUrl}/${wellPath}/${imagePath}`;

  const layerCreatedTime = useRef<number | undefined>(undefined);
  const loadAllSlicesClickedTime = useRef<number | undefined>(undefined);

  const [selectedTomogram, setSelectedTomogram] = useState<string | null>(null);
  const [tomogramDetail, setTomogramDetail] = useState<ReviewTomogramDetail | null>(null);
  const [contrast, setContrast] = useState(50);
  const [slabThickness, setSlabThickness] = useState(1000);
  const [zPosition, setZPosition] = useState(50);
  const [seriesDimensionName, setSeriesDimensionName] = useState('Z');

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

      const mockResponse = {
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
    <div className="flex flex-col items-center min-h-screen gap-8 py-10 px-6">
      <TopBar onMarkComplete={() => console.log('Mark as complete')} />
      <div className="flex flex-row gap-6">
        <SideBar
          reviewName={review.reviewName}
          tomograms={review.tomograms}
          selectedTomogram={selectedTomogram}
          currentIndex={currentIndex}
          onPrevious={handlePrevious}
          onNext={handleNext}
          onSelectTomogram={setSelectedTomogram}
          contrast={contrast}
          onContrastChange={setContrast}
          slabThickness={slabThickness}
          onSlabThicknessChange={setSlabThickness}
        />

        <div className="flex flex-col flex-1 p-6 rounded">
          {selectedTomogram ? (
            <>
              <div className="flex-1 flex items-center justify-center border-r border-l">
                <OmeZarrImageViewer
                  sourceUrl={imageUrl}
                  region={region}
                  seriesDimensionName="Z"
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

              <div className="flex items-center gap-4 p-4 rounded mt-6 border">
                <Button sdsStyle="square" size="small">
                  ←
                </Button>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={zPosition}
                  onChange={(e) => setZPosition(Number(e.target.value))}
                  className="flex-1"
                />
                <Button sdsStyle="square" size="small">
                  →
                </Button>
              </div>
            </>
          ) : (
            <div className="p-6 bg-white rounded">Select a tomogram to view</div>
          )}
        </div>

        <div className=" p-4rounded">
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
