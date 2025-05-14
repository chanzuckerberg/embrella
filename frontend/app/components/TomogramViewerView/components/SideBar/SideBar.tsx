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
  selectedTomogram: string | null;
  currentIndex: number;
  onPrevious: () => void;
  onNext: () => void;
  onSelectTomogram: (tomogramId: string) => void;
  contrast: number;
  onContrastChange: (value: number) => void;
  slabThickness: number;
  onSlabThicknessChange: (value: number) => void;
  imageIndex: number;
  setImageIndex: (index: number) => void;
  imagePaths: string[];
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
  imageIndex,
  setImageIndex,
  imagePaths,
}: SideBarProps) => {
  return (
    <div className="flex flex-1 flex-col justify-start gap-8">
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
