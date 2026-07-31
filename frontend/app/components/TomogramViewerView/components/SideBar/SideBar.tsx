import React, { useState } from 'react';
import { SideBarSection } from './components/SideBarSection';
import { NavigationButtons } from './components/NavigationButtons';
import { TomogramTable } from './components/TomogramTable';
import { TomogramInfo } from './components/TomogramInfo';
import { SliderControls } from './components/SliderControls';
import { ChannelControlsList } from '@idetik/react';
import { ChannelsEnabled } from '@idetik/core';
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
  showSliderSection?: boolean;
  assessmentSlot?: React.ReactNode;
  // Z-navigation props
  currentZIndex?: number;
  zAxisMetadata?: { min: number; max: number; count: number };
  onZIndexChange?: (zIndex: number) => void;
  // Channel controls props
  channelLayer?: ChannelsEnabled | null;
  extraControlProps?: Array<{ label: string; contrastRange: [number, number] }>;
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
  showSliderSection = true,
  assessmentSlot,
  currentZIndex,
  zAxisMetadata,
  onZIndexChange,
  channelLayer,
  extraControlProps,
}: SideBarProps) => {
  const reviewedCount = tomograms.filter((t) => t.status !== 'pending').length;

  const [infoOpen, setInfoOpen] = useState(true);
  const [sliderOpen, setSliderOpen] = useState(true);

  return (
    <div className="basis-[280px] max-lg:basis-auto max-lg:w-full shrink-0 flex flex-col justify-start divide-y-[2px]">
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
        {!assessmentSlot && (
          <NavigationButtons
            currentIndex={currentIndex}
            totalItems={tomograms.length}
            onPrevious={onPrevious}
            onNext={onNext}
          />
        )}
      </SideBarSection>

      {assessmentSlot}

      <SideBarSection>
        <TomogramInfo tomogramDetail={tomogramDetail} open={infoOpen} setOpen={setInfoOpen} />
      </SideBarSection>
      {showSliderSection && (
        <SideBarSection>
          <SliderControls
            open={sliderOpen}
            setOpen={setSliderOpen}
            currentZIndex={currentZIndex}
            zAxisMetadata={zAxisMetadata}
            onZIndexChange={onZIndexChange}
          />
        </SideBarSection>
      )}
      <SideBarSection className="overflow-visible [&_#channel-controls]:w-full [&_.MuiAccordionSummary-content]:!m-0 [&_.MuiAccordionSummary-root]:!p-0 [&_.MuiAccordionSummary-root]:!min-h-0 [&_.MuiAccordionDetails-root]:!p-0 [&_.MuiAccordionDetails-root]:!pt-4 [&_.MuiAccordion-root]:!bg-transparent [&_.MuiAccordion-root]:before:!hidden [&_.MuiAccordionSummary-expandIconWrapper]:!hidden [&_.MuiCollapse-root]:!block [&_.MuiCollapse-root]:!h-auto [&_.MuiCollapse-root]:!visible [&_.MuiCollapse-wrapper]:!block">
        {channelLayer && extraControlProps && extraControlProps.length > 0 ? (
          <ChannelControlsList
            layer={channelLayer}
            extraControlProps={extraControlProps}
            classNames={{
              root: '!bg-transparent !shadow-none !m-0 !p-0 !rounded-none !w-full !flex-col [&_div.flex.items-center.text-white]:!text-black [&_div.flex.items-center.text-white]:!font-bold [&_div.flex.items-center.text-white]:!text-lg',
            }}
          />
        ) : (
          <div className="text-gray-500 text-sm">Loading channel controls...</div>
        )}
      </SideBarSection>
    </div>
  );
};
