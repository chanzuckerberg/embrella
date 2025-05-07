/* eslint-disable @typescript-eslint/no-unused-vars */

'use client';

import { Button } from '@czi-sds/components';
import Link from 'next/link';
import { useState, useEffect, useRef, useCallback } from 'react';
import { useOmeZarrViewer, Renderer, OmeZarrImageViewer } from '@idetik/react';
import { LayerManager, OrthographicCamera, Region } from '@idetik/core';
import { ReviewTomogramDetail } from './types';

export interface User {
  id: string | number; // Can be UUID or number
  name: string;
}

export interface ReviewTomogramSummary {
  tomogramId: string;
  status: 'pending' | 'accepted' | 'rejected' | 'uncertain';
}

export interface Review {
  reviewId: string; // UUID
  reviewName: string;
  owner: User;
  tomograms: ReviewTomogramSummary[];
}

export interface TomogramViewerProps {
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

export const TomogramViewer = ({ review }: TomogramViewerProps) => {
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

  console.log('imageUrl', imageUrl);
  const valid = imagePath && sourceUrl && wellPath;
  const shouldLoad = valid && selectedTomogram !== null;
  // if (!imagePath || !sourceUrl || !wellPath) {
  //     return <div>Loading...</div>;
  // }

  const {
    layerManager,
    camera,
    imageLayer,
    controlProps,
    zRange,
    zValue,
    zIndex,
    setZValue,
    loading,
    allSlicesLoaded,
    resetChannelsCallback,
    loadAllSlicesCallback,
  } = useOmeZarrViewer({
    sourceUrl,
    region,
    seriesDimensionName,
    onLayerCreated: handleLayerCreated,
    onFirstSliceLoaded: handleFirstSliceLoaded,
    onLoadAllSlicesClicked: handleLoadAllSlicesClicked,
    onAllSlicesLoaded: handleAllSlicesLoaded,
    onLoadAllSlicesAborted: handleLoadAllSlicesAborted,
  });

  // Add the image layer to the layer manager when it's created
  useEffect(() => {
    if (imageLayer) {
      layerManager.add(imageLayer);
    }
  }, [imageLayer, layerManager]);

  return (
    <div className="flex flex-col h-screen w-full">
      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 flex flex-col bg-gray-100 p-4">
          <>
            <div
              style={{
                flex: 1,
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <div style={{ width: '100%', height: '100%', position: 'relative' }}>
                {/* <OmeZarrImageViewer
                                    sourceUrl={imageUrl}
                                    region={region}
                                    seriesDimensionName="Z"
                                    allSlicesSizeEstimate="250 MB"
                                    onLayerCreated={handleLayerCreated}
                                    onFirstSliceLoaded={handleFirstSliceLoaded}
                                    onLoadAllSlicesClicked={handleLoadAllSlicesClicked}
                                    onAllSlicesLoaded={handleAllSlicesLoaded}
                                    onLoadAllSlicesAborted={handleLoadAllSlicesAborted}
                                /> */}
                <Renderer
                  layerManager={layerManager}
                  camera={camera}
                  cameraControls="panzoom"
                  canvasId="tomogram-viewer-canvas"
                />
              </div>
            </div>
            <div className="flex items-center gap-4 p-4 bg-white rounded mt-4">
              <Button size="small">←</Button>
              <input
                type="range"
                min="0"
                max="100"
                value={zPosition}
                onChange={(e) => setZPosition(Number(e.target.value))}
                style={{ flex: 1 }}
              />
              <Button size="small">→</Button>
            </div>
          </>
        </div>
      </div>
    </div>
  );
};
