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
  contrast: [number, number];
  onContrastChange: (value: [number, number]) => void;
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
  contrast,
  onContrastChange,
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
        <TomogramInfo tomogramDetail={tomogramDetail} />
        <SliderControls contrast={contrast} onContrastChange={onContrastChange} />
      </SideBarSection>
    </div>
  );
};
