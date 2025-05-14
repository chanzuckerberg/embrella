import { SideBarSection } from './components/SideBarSection';
import { NavigationButtons } from './components/NavigationButtons';
import { TomogramTable } from './components/TomogramTable';
import { TomogramInfo } from './components/TomogramInfo';
import { SliderControls } from './components/SliderControls';
import { ReviewTomogramSummary } from '../../types';
// import { ChannelControlsList } from '../../../../../imaging-active-learning/packages/react/src/components/viewers/OmeZarrImageViewer/components/ChannelControlsList';

interface SideBarProps {
  reviewName: string;
  tomograms: ReviewTomogramSummary[];
  selectedTomogram?: string;
  currentIndex: number;
  onPrevious: () => void;
  onNext: () => void;
  onSelectTomogram: (tomogramId: string) => void;
  contrast: [number, number];
  onContrastChange: (value: [number, number]) => void;
  slabThickness: number;
  onSlabThicknessChange: (value: number) => void;
}

export const SideBar = ({
  reviewName,
  tomograms,
  selectedTomogram,
  currentIndex,
  onPrevious,
  onNext,
  onSelectTomogram,
  contrast,
  onContrastChange,
  slabThickness,
  onSlabThicknessChange,
}: SideBarProps) => {
  return (
    <div className="basis-[280px] shrink-0 flex flex-col justify-start gap-8 !p-[20px]">
      <SideBarSection>
        <div className="flex flex-col">
          <h2 className="p-8">{reviewName}</h2>
          <p className="text-sm text-gray-500">0 of {tomograms.length} Tomograms Reviewed</p>
        </div>
      </SideBarSection>

      <SideBarSection>
        <TomogramTable tomograms={tomograms} selectedTomogram={selectedTomogram} onSelectTomogram={onSelectTomogram} />
        <NavigationButtons
          currentIndex={currentIndex}
          totalItems={tomograms.length}
          onPrevious={onPrevious}
          onNext={onNext}
        />
      </SideBarSection>

      <SideBarSection>
        <TomogramInfo tomogramId={selectedTomogram || ''} />
        <SliderControls
          contrast={contrast}
          onContrastChange={onContrastChange}
          slabThickness={slabThickness}
          onSlabThicknessChange={onSlabThicknessChange}
        />
      </SideBarSection>
      {/* <SideBarSection>
        <ChannelControlsList
        />
        <input
          type="button"
          value="Switch Image"
          onClick={() => setImageIndex((imageIndex + 1) % imagePaths.length)}
          className="h-12"
        />
      </SideBarSection> */}
    </div>
  );
};
