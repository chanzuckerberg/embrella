"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { TopBar } from "./components/TopBar";
import { Sidebar } from "./components/Sidebar";
import { ViewerContainer, MainContent, ViewerArea, ZSliderContainer } from "./style";
import { Button } from "@czi-sds/components";
import { Review, ReviewTomogramDetail } from "./types";
import { QualityControls } from "./components/QualityControls";
import { OmeZarrImageViewer } from "@idetik/react";
import { LayerManager, OrthographicCamera, Region } from "@idetik/core";



interface TomogramViewerProps {
    review: Review;
}

const sourceUrl =
    "https://public.czbiohub.org/organelle_box/datasets/A549/organelle_box_crop_v1.zarr";
const wellPath = "ATG101/MeOH";
const region: Region = [
    { dimension: "T", index: { type: "point", value: 0 } },
    { dimension: "C", index: { type: "full" } },
    { dimension: "Z", index: { type: "full" } },
    { dimension: "Y", index: { type: "full" } },
    { dimension: "X", index: { type: "full" } },
];
const imagePaths = ["000000", "000001", "000002", "001000", "001001", "001002"];

export const TomogramViewer = ({ review }: TomogramViewerProps) => {
    const [selectedTomogram, setSelectedTomogram] = useState<string | null>(null);
    const [tomogramDetail, setTomogramDetail] = useState<ReviewTomogramDetail | null>(null);
    const [contrast, setContrast] = useState(50);
    const [slabThickness, setSlabThickness] = useState(1000);
    const [zPosition, setZPosition] = useState(50);
    const [imageIndex, setImageIndex] = useState(0);
    const [layerManager, setLayerManager] = useState<LayerManager>(
        new LayerManager()
    );
    const [camera, setCamera] = useState<OrthographicCamera | null>(null);

    const imagePath = imagePaths[imageIndex];
    const imageUrl = `${sourceUrl}/${wellPath}/${imagePath}`;

    const layerCreatedTime = useRef<number | undefined>(undefined);
    const loadAllSlicesClickedTime = useRef<number | undefined>(undefined);


    const handleLayerCreated = useCallback(() => {
        layerCreatedTime.current = performance.now();
        console.log(`Layer created at ${layerCreatedTime.current}`);
    }, []);

    const handleFirstSliceLoaded = useCallback(() => {
        if (layerCreatedTime.current !== undefined) {
            const time = performance.now() - layerCreatedTime.current;
            console.log(`First slice loaded after ${time} ms`);
        } else {
            console.log("First slice loaded, but layer created time is undefined");
        }
    }, []);

    const handleLoadAllSlicesClicked = useCallback(() => {
        loadAllSlicesClickedTime.current = performance.now();
        console.log(
            `Load all slices clicked at ${loadAllSlicesClickedTime.current}`
        );
    }, []);

    const handleAllSlicesLoaded = useCallback(() => {
        if (loadAllSlicesClickedTime.current !== undefined) {
            const time = performance.now() - loadAllSlicesClickedTime.current;
            console.log(`All slices loaded after ${time} ms`);
        } else {
            console.log(
                "All slices loaded, but load all slices clicked time is undefined"
            );
        }
    }, []);

    const handleLoadAllSlicesAborted = useCallback(() => {
        if (loadAllSlicesClickedTime.current !== undefined) {
            const time = performance.now() - loadAllSlicesClickedTime.current;
            console.log(`Load all slices aborted after ${time} ms`);
        } else {
            console.log(
                "Load all slices aborted, but load all slices clicked time is undefined"
            );
        }
    }, []);

    const currentIndex = selectedTomogram
        ? review.tomograms.findIndex((t) => t.tomogramId === selectedTomogram)
        : -1;

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
                    quality: "uncertain" as const,
                },
            };

            setTomogramDetail(mockResponse);
        };

        fetchTomogramDetail();
    }, [selectedTomogram]);

    return (
        <ViewerContainer>
            <TopBar onMarkComplete={() => console.log("Mark as complete")} />

            <MainContent>
                <Sidebar
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

                <ViewerArea>
                    {selectedTomogram ? (
                        <>
                            <div
                                style={{
                                    flex: 1,
                                    width: "100%",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                }}
                            >
                                <OmeZarrImageViewer
                                    sourceUrl={imageUrl}
                                    region={region}
                                    seriesDimensionName="Z"
                                    allSlicesSizeEstimate="250 MB"
                                    onLayerCreated={handleLayerCreated}
                                    onFirstSliceLoaded={handleFirstSliceLoaded}
                                    onLoadAllSlicesClicked={handleLoadAllSlicesClicked}
                                    onAllSlicesLoaded={handleAllSlicesLoaded}
                                    onLoadAllSlicesAborted={handleLoadAllSlicesAborted}
                                />
                                {/* <Renderer
                                    layerManager={layerManager}
                                    camera={camera}
                                /> */}
                            </div>
                            <ZSliderContainer>
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
                            </ZSliderContainer>
                        </>
                    ) : (
                        <div>Select a tomogram to view</div>
                    )}
                </ViewerArea>

                <QualityControls
                    onAccept={() => console.log("Accept")}
                    onReject={() => console.log("Reject")}
                    onUncertain={() => console.log("Uncertain")}
                />
            </MainContent>
        </ViewerContainer>
    );
};