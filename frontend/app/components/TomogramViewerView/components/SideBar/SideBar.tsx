import React, { useState } from 'react';
import { SideBarSection } from './components/SideBarSection';
import { NavigationButtons } from './components/NavigationButtons';
import { TomogramTable } from './components/TomogramTable';
import { TomogramInfo } from './components/TomogramInfo';
import { SliderControls } from './components/SliderControls';
import { ReviewTomogramSummary, TomogramDetail } from '../../types';

interface SideBarProps {
  reviewName: string;
  tomograms: ReviewTomogramSummary[];
  selectedTomogram?: string;
  tomogramDetail: TomogramDetail | null;
  currentIndex: number;
  onPrevious: () => void;
  onNext: () => void;
  onSelectTomogram: (tomogramId: string) => void;
  contrastLimits: [number, number];
  onContrastLimitsChange: (value: [number, number]) => void;
  contrastRange?: [number, number]; // Dynamic range for the slider
}

export const SideBar = ({
  reviewName,
  tomograms,
  selectedTomogram,
  tomogramDetail,
  currentIndex,
  onPrevious,
  onNext,
  onSelectTomogram,
  contrastLimits: contrast,
  onContrastLimitsChange: onContrastChange,
  contrastRange,
}: SideBarProps) => {
  const reviewedCount = tomograms.filter((t) => t.status !== 'pending').length;

  const [infoOpen, setInfoOpen] = useState(true);
  const [sliderOpen, setSliderOpen] = useState(true);

  return (
    <div className="basis-[280px] shrink-0 flex flex-col justify-start divide-y-[2px]">
      <SideBarSection>
        <div className="flex flex-col gap-[10px]">
          <h2 className="font-bold text-xl leading-tight">
            {reviewName} <br />
          </h2>
          <div className="text-[#767676]">
            {reviewedCount} of {tomograms.length} Tomograms Reviewed
          </div>
        </div>
      </SideBarSection>

      <SideBarSection className="min-h-0">
        <TomogramTable tomograms={tomograms} selectedTomogram={selectedTomogram} onSelectTomogram={onSelectTomogram} />
        <NavigationButtons
          currentIndex={currentIndex}
          totalItems={tomograms.length}
          onPrevious={onPrevious}
          onNext={onNext}
        />
      </SideBarSection>

      <SideBarSection>
        <TomogramInfo tomogramDetail={tomogramDetail} open={infoOpen} setOpen={setInfoOpen} />
      </SideBarSection>
      <SideBarSection>
        <SliderControls
          contrast={contrast}
          onContrastChange={onContrastChange}
          open={sliderOpen}
          setOpen={setSliderOpen}
          contrastRange={contrastRange}
        />
      </SideBarSection>
    </div>
  );
};
