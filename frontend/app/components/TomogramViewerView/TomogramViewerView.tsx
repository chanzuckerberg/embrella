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
import { useIdetik } from '../../../imaging-active-learning/packages/react/src/components/hooks';
import { API, MOCKED_APIS, POST_API, MOCKED_POST_APIS } from '../../../app/common/constants/api';
import { RejectionReasonsSelector } from './components/RejectionReasonsSelector';
import { ObjectLabelsSelector } from './components/ObjectLabelsSelector';
import { AVAILABLE_ANNOTATION_OBJECTS } from '../CreateReviewView/CreateReviewView';

interface TomogramViewerProps {
    review: Review;
}

export const TomogramViewerView = ({ review }: TomogramViewerProps) => {
    const [region, setRegion] = useState<Region | null>(null);

    const layerCreatedTime = useRef<number | undefined>(undefined);
    const loadAllSlicesClickedTime = useRef<number | undefined>(undefined);

    const [selectedTomogram, setSelectedTomogram] = useState<string | undefined>(review.tomograms[0]?.tomogramId);
    const [tomogramDetail, setTomogramDetail] = useState<ReviewTomogramDetail | null>(null);
    const [seriesDimensionName, setSeriesDimensionName] = useState('z');
    const [contrastLimits, setContrastLimits] = useState<[number, number]>([-0.00001, 0.00001]);
    const [selectedRejectionReasons, setSelectedRejectionReasons] = useState<string[]>([]);
    const [selectedQuality, setSelectedQuality] = useState<"accepted" | "rejected" | "uncertain" | null>(null);
    const [selectedObjectLabels, setSelectedObjectLabels] = useState<string[]>([]);

    const { imageSeriesLayer, channels } = useIdetik();
    const handleContrastLimitsChange = useCallback(
        (newLimits: [number, number]) => {
            if (!imageSeriesLayer) return;

            const updatedChannels = channels.map((channel) => ({
                ...channel,
                contrastLimits: newLimits,
            }));
            setContrastLimits(newLimits);
            imageSeriesLayer.setChannelProps(updatedChannels);
        },
        [imageSeriesLayer, channels]
    );

    useEffect(() => {
        const fetchRegion = async () => {
            if (!tomogramDetail?.zarrPath) return;
            const region = await getRegionFromZattrs(tomogramDetail.zarrPath);
            console.log("region", region)
            setRegion(region);
        };
        fetchRegion();
    }, [tomogramDetail?.zarrPath]);

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

            // List of allowed tomogram IDs for the mock
            const allowedTomograms = ['tomo_001', 'tomo_002', 'tomo_003'];

            // If selectedTomogram is not in the allowed list, pick a random one
            const tomogramIdToUse = allowedTomograms.includes(selectedTomogram)
                ? selectedTomogram
                : allowedTomograms[Math.floor(Math.random() * allowedTomograms.length)];

            const url = `/api/reviews/${review.reviewId}/tomograms/${tomogramIdToUse}`;

            const tomogramDetail =
                typeof MOCKED_APIS[API.TOMOGRAM_DETAIL] === 'function'
                    ? MOCKED_APIS[API.TOMOGRAM_DETAIL](url)
                    : null;

            if (tomogramDetail) {
                setTomogramDetail(tomogramDetail);
            } else {
                setTomogramDetail(null);
            }
        };
        fetchTomogramDetail();
    }, [selectedTomogram]);

    const handleTomogramReview = (
        quality: "accepted" | "rejected" | "uncertain",
        rejectionReasons?: string[]
    ) => {
        if (!selectedTomogram) return;
        const payload = {
            tomogramId: selectedTomogram,
            quality,
            ...(rejectionReasons ? { rejectionReasons } : {}),
        };
        const response = MOCKED_POST_APIS[POST_API.UPDATE_TOMOGRAM_REVIEW](payload);
        console.log('Review response:', response);
        setSelectedQuality(null);
        setSelectedRejectionReasons([]);

        // Move to the next tomogram if there is one
        if (currentIndex < review.tomograms.length - 1) {
            setSelectedTomogram(review.tomograms[currentIndex + 1].tomogramId);
        }
    };

    return (
        <div className="flex flex-col items-center">
            <div className="flex flex-col justify-between h-[60vh] md:h-[90vh] lg:h-[90vh] items-center gap-8 w-[80vw]">
                <div className="h-6"></div>
                < TopBar onMarkComplete={() => console.log('Mark as complete')} />
                < div className="flex-auto flex border-t border-gray-400" >
                    <SideBar
                        reviewName={review.reviewName}
                        tomograms={review.tomograms}
                        selectedTomogram={selectedTomogram}
                        tomogramDetail={tomogramDetail}
                        currentIndex={currentIndex}
                        onPrevious={handlePrevious}
                        onNext={handleNext}
                        onSelectTomogram={setSelectedTomogram}
                        contrastLimits={contrastLimits}
                        onContrastLimitsChange={handleContrastLimitsChange}
                    />
                    <div className="flex-auto flex flex-col p-6 rounded items-center justify-center">
                        {/* {selectedTomogram && region ? ( */}
                        <>
                            <div className="border-r border-l">
                                <div className="w-[60vh] md:w-[75vh] lg:w-[80vh] h-[60vh] md:h-[75vh] lg:h-[80vh]">
                                    <OmeZarrImageViewer
                                        sourceUrl={tomogramDetail?.zarrPath || ''}
                                        region={region || []}
                                        seriesDimensionName={seriesDimensionName}
                                        allSlicesSizeEstimate="250 MB"
                                        fallbackContrastLimits={contrastLimits}
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
                            </div>
                        </>
                        {/* ) : (
                            <div className="p-6 bg-white rounded">Select a tomogram to view</div>
                        )} */}
                    </div>
                    <div className="flex flex-col">
                        <div className="basis-[250px] shrink-0 !pt-[20px] !pr-[20px] !pl-[20px] !pb-0">
                            <QualityControls
                                selectedQuality={selectedQuality}
                                onAccept={() => { setSelectedQuality("accepted"); }}
                                onReject={() => { setSelectedQuality("rejected"); }}
                                onUncertain={() => handleTomogramReview("uncertain")}
                            />
                        </div>
                        {selectedQuality === "rejected" && (
                            <div className="basis-[250px] shrink-0 !pb-[20px] !pr-[20px] !pl-[20px] !pt-0">
                                <RejectionReasonsSelector
                                    selectedReasons={selectedRejectionReasons}
                                    setSelectedReasons={setSelectedRejectionReasons}
                                    onChange={(_, selected) => handleTomogramReview("rejected", selected)}
                                />
                            </div>
                        )}
                        {selectedQuality === "accepted" && (
                            <div className="basis-[250px] shrink-0 !pb-[20px] !pr-[20px] !pl-[20px] !pt-0">
                                <ObjectLabelsSelector
                                    availableObjects={AVAILABLE_ANNOTATION_OBJECTS}
                                    selectedObjects={selectedObjectLabels}
                                    setSelectedObjects={setSelectedObjectLabels}
                                    onChange={(_,) => handleTomogramReview("accepted", selectedObjectLabels)}
                                />
                            </div>
                        )}
                    </div>
                </div >
            </div >
        </div >
    );
};
